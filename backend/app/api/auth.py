"""Authentication and health endpoints.

Provides:
* ``GET /api/v1/health`` — public service health check.
* ``POST /api/v1/auth/demo-login`` — localhost-only demo JWT issuance
  (disabled in production and from non-localhost addresses).

In production, JWT verification against Keycloak OIDC is handled by the
``get_current_user`` dependency in ``core.auth`` — the same tokens issued
by demo-login are validated identically, so the auth boundary is
unchanged when Keycloak is introduced.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.core.auth import generate_demo_token, verify_demo_mode
from app.core.config import get_settings
from app.models.schemas import HealthResponse, TokenResponse

router = APIRouter(tags=["auth"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Public health endpoint returning service status and config flags."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        demo_mode=settings.demo_allowed(),
    )


@router.post("/auth/demo-login", response_model=TokenResponse)
def demo_login(
    request: Request,
    role: str = "operator",
) -> TokenResponse:
    """Issue a demo JWT token for localhost development.

    Hard-gated: returns 403 when demo mode is disabled (production) or
    when the request does not originate from a loopback address.
    """
    if not verify_demo_mode(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode is disabled or not accessible from this address",
        )
    if role not in ("viewer", "operator", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role}",
        )
    token = generate_demo_token(role)
    return TokenResponse(access_token=token, token_type="bearer", role=role)


@router.post("/auth/demo-key", response_model=TokenResponse)
def demo_key() -> TokenResponse:
    """Provide a pre-generated demo token for API documentation testing.

    This endpoint is also gated by demo mode.  It returns a viewer-level
    token suitable for read-only endpoints.
    """
    settings = get_settings()
    if not settings.demo_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode is disabled",
        )
    token = generate_demo_token("viewer")
    return TokenResponse(access_token=token, token_type="bearer", role="viewer")