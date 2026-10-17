"""Tests for authentication, authorization, and system-level behavior.

Covers: unauthenticated rejection, role denial, demo mode production
lockout, token tampering detection, and health endpoint behavior.
"""

from __future__ import annotations

import os
import sys

import pytest

from app.core.auth import (
    create_access_token,
    decode_access_token,
    generate_demo_token,
    verify_demo_mode,
    User,
    ROLE_HIERARCHY,
)
from app.core.config import Settings


VALID_PAYLOAD = {
    "style_archetype": "cinematic-portrait",
    "subject": "test subject",
    "mood": "dramatic",
    "lighting": "three-point-studio",
    "composition": "close-up",
    "quality": "standard",
}


class TestTokenGenerationAndVerification:
    """Core JWT encoding and decoding round-trips."""

    def test_token_round_trip(self):
        token = create_access_token("test-subject", role="operator")
        payload = decode_access_token(token)
        assert payload["sub"] == "test-subject"
        assert payload["role"] == "operator"

    def test_token_contains_expiry(self):
        token = create_access_token("test-subject", role="viewer")
        payload = decode_access_token(token)
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_demo_token_has_demo_flag(self):
        token = generate_demo_token("viewer")
        payload = decode_access_token(token)
        assert payload["demo"] is True

    def test_invalid_token_raises(self):
        import jwt as pyjwt
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_access_token("not-a-valid-jwt")


class TestRoleHierarchy:
    """Role-based authorization must respect the hierarchy: admin > operator > viewer."""

    def test_admin_can_access_operator_endpoints(self):
        user = User("admin", "admin")
        assert user.has_role("viewer", "operator")

    def test_operator_cannot_access_admin(self):
        user = User("op", "operator")
        assert not user.has_role("admin")

    def test_viewer_cannot_create(self):
        user = User("v", "viewer")
        assert not user.has_role("operator")
        assert user.has_role("viewer")


class TestDemoModeLockout:
    """Demo mode must be disabled in production and from non-localhost."""

    def test_demo_disabled_in_production(self):
        """When ENVIRONMENT=production, demo mode is refused even if DEMO_MODE=true."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["DEMO_MODE"] = "true"
        # Force re-evaluation
        from app.core.config import get_settings as _get
        _get.cache_clear()
        settings = Settings()
        assert settings.is_production() is True
        assert settings.demo_allowed() is False
        # Restore
        os.environ["ENVIRONMENT"] = "development"
        _get.cache_clear()

    def test_demo_allowed_in_development(self):
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DEMO_MODE"] = "true"
        from app.core.config import get_settings as _get
        _get.cache_clear()
        settings = Settings()
        assert settings.demo_allowed() is True
        _get.cache_clear()


class TestUnauthenticatedRejection:
    """All protected endpoints must reject requests without a valid token."""

    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/v1/intents/"),
        ("POST", "/api/v1/intents/"),
        ("GET", "/api/v1/intents/some-id"),
        ("POST", "/api/v1/intents/some-id/compile"),
        ("GET", "/api/v1/audit/"),
        ("POST", "/api/v1/evaluation/run"),
    ])
    def test_endpoint_rejects_no_token(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401


class TestRoleDenial:
    """Insufficient roles must return 403."""

    def test_viewer_cannot_create_intent(self, client, viewer_headers):
        resp = client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=viewer_headers)
        assert resp.status_code == 403

    def test_viewer_cannot_delete(self, client, viewer_headers):
        # Create first as operator
        from app.core.auth import generate_demo_token
        op_token = generate_demo_token("operator")
        op_headers = {"Authorization": f"Bearer {op_token}"}
        create = client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=op_headers)
        intent_id = create.json()["id"]
        # Now try to delete as viewer
        resp = client.delete(f"/api/v1/intents/{intent_id}", headers=viewer_headers)
        assert resp.status_code == 403

    def test_operator_cannot_access_audit(self, client, auth_headers):
        resp = client.get("/api/v1/audit/", headers=auth_headers)
        assert resp.status_code == 403

    def test_operator_can_access_intents(self, client, auth_headers):
        resp = client.get("/api/v1/intents/", headers=auth_headers)
        assert resp.status_code == 200

    def test_admin_can_access_audit(self, client, admin_headers):
        resp = client.get("/api/v1/audit/", headers=admin_headers)
        assert resp.status_code == 200


class TestTokenTampering:
    """Tampered or expired tokens must be rejected."""

    def test_tampered_token_rejected(self, client):
        token = generate_demo_token("operator")
        # Tamper: flip a character in the payload
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1][:-1] + "X" + "." + parts[2]
        resp = client.get(
            "/api/v1/intents/",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert resp.status_code == 401

    def test_expired_token_rejected(self, client):
        from datetime import datetime, timedelta, timezone
        from app.core.auth import _signing_key, ALGORITHM
        import jwt as pyjwt

        settings = Settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "expired-user",
            "role": "viewer",
            "exp": now - timedelta(hours=1),
            "iat": now - timedelta(hours=2),
        }
        token = pyjwt.encode(payload, _signing_key(), algorithm=ALGORITHM)
        resp = client.get(
            "/api/v1/intents/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401


class TestHealthAndSystem:
    """System-level endpoint behavior."""

    def test_health_returns_version(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "1.0.0"
        assert data["status"] == "ok"

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Orbit Forge"

    def test_version_endpoint(self, client):
        resp = client.get("/version")
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.0.0"