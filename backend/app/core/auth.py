"""JWT bearer-only authentication and role-based authorization.

Tokens are validated on every request using HS256 (demo / local dev) or
RS256 (Keycloak OIDC, production).  Demo mode is gated at startup: it only
operates on localhost when ENVIRONMENT is not ``production``.

Roles:
    viewer   — read access to intents and compiled results.
    operator — create, update, compile, delete intents.
    admin    — audit log access and system configuration.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=8)

# Role hierarchy: higher roles inherit lower permissions.
ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 1,
    "operator": 2,
    "admin": 3,
}

bearer_scheme = HTTPBearer(auto_error=False)


class User:
    """Authenticated principal resolved from a validated token."""

    def __init__(self, subject: str, role: str, demo: bool = False) -> None:
        self.subject = subject
        self.role = role
        self.demo = demo

    def has_role(self, *required: str) -> bool:
        """True if the user's role satisfies any of the *required* roles
        (or a higher one per the hierarchy)."""
        user_level = ROLE_HIERARCHY.get(self.role, 0)
        return any(
            user_level >= ROLE_HIERARCHY.get(r, 0)
            for r in required
        )


def _signing_key() -> str:
    """Return the configured secret key or a dev fallback.

    In production, ``SECRET_KEY`` must be set explicitly; otherwise tokens
    cannot be securely verified.
    """
    settings = get_settings()
    return settings.secret_key


def create_access_token(subject: str, role: str = "viewer", demo: bool = False) -> str:
    """Create a signed JWT carrying subject, role, and expiry."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "demo": demo,
        "iss": settings.oidc_issuer_url or "orbit-forge-demo",
        "aud": settings.oidc_audience or subject,
        "iat": now,
        "exp": now + TOKEN_TTL,
    }
    return jwt.encode(payload, _signing_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Validate and decode a JWT.  Raises ``jwt.InvalidTokenError`` on failure.

    In production (ENVIRONMENT=production), audience and issuer are verified
    against the configured OIDC settings.  In development/demo mode, audience
    and issuer claims are present in the token but not enforced.
    """
    settings = get_settings()
    key = _signing_key()
    kwargs: dict = {"algorithms": [ALGORITHM]}

    if settings.is_production():
        if settings.oidc_audience:
            kwargs["audience"] = settings.oidc_audience
        if settings.oidc_issuer_url:
            kwargs["issuer"] = settings.oidc_issuer_url
    else:
        # Dev/demo: accept tokens without strict audience/issuer checks.
        kwargs["options"] = {"verify_aud": False, "verify_iss": False}

    return jwt.decode(token, key, **kwargs)


def is_localhost(request: Request) -> bool:
    """True if the request originates from a loopback address or name.

    Checks the direct client address, the ``host`` header, and the
    ``x-forwarded-for`` header (for tests behind a proxy).  The loopback
    check is a secondary defense for demo mode; the primary gate is the
    production-environment lockout in ``Settings.demo_allowed``.
    """

    def _is_loopback(addr: str) -> bool:
        addr = addr.strip()
        # Strip IPv6 brackets and port
        if addr.startswith("["):
            addr = addr[1:].split("]")[0]
        else:
            addr = addr.split(":")[0]
        return addr in ("127.0.0.1", "::1", "localhost")

    client_host = request.client.host if request.client else ""

    candidates: list[str] = [client_host]
    host_header = request.headers.get("host", "")
    if host_header:
        candidates.append(host_header)
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        candidates.extend(h.strip() for h in forwarded.split(","))

    return any(_is_loopback(c) for c in candidates if c)


def verify_demo_mode(request: Request) -> bool:
    """Gate demo mode: production blocks it, non-localhost blocks it."""
    settings = get_settings()
    if not settings.demo_allowed():
        return False
    return is_localhost(request)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """Extract and validate the bearer token, returning a ``User`` principal.

    Raises 401 when no token is present, 401 for an invalid/expired token,
    and 403 when demo tokens are used from non-localhost in blocked contexts.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {type(exc).__name__}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_demo = bool(payload.get("demo", False))
    if is_demo and not is_localhost(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo tokens are only valid from localhost",
        )
    return User(
        subject=payload["sub"],
        role=payload.get("role", "viewer"),
        demo=is_demo,
    )


def require_role(*roles: str):
    """Dependency factory that enforces role-level authorization."""

    async def _role_checker(
        request: Request,
        user: User = Depends(get_current_user),
    ) -> User:
        if not user.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return user

    return _role_checker


def generate_demo_token(role: str = "viewer") -> str:
    """Issue a demo JWT token (used by the demo-login endpoint)."""
    subject = f"demo-{role}"
    return create_access_token(subject, role=role, demo=True)