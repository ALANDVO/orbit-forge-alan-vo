"""Integration tests for the intent REST API.

Covers the full create → list → get → compile lifecycle, pagination,
filtering, malformed-input rejection, and the cross-boundary HTTP flow
from the TestClient.
"""

from __future__ import annotations

import pytest

from app.models.domain import IntentDefinition


VALID_PAYLOAD = {
    "style_archetype": "cinematic-portrait",
    "subject": "a woman with freckles wearing a leather jacket",
    "mood": "dramatic",
    "lighting": "three-point-studio",
    "composition": "close-up",
    "quality": "standard",
}


class TestCreateGetCompile:
    """End-to-end workflow: create intent, retrieve it, compile, retrieve compiled."""

    def test_create_intent(self, client, auth_headers):
        resp = client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["style_archetype"] == "cinematic-portrait"
        assert data["subject"] == VALID_PAYLOAD["subject"]
        assert data["id"].startswith("int_")
        assert "created_at" in data

    def test_list_intents(self, client, auth_headers):
        client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/v1/intents/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["intents"]) >= 2

    def test_get_single_intent(self, client, auth_headers):
        create = client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        intent_id = create.json()["id"]
        resp = client.get(f"/api/v1/intents/{intent_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == intent_id
        assert data["mood"] == "dramatic"

    def test_get_nonexistent_intent(self, client, auth_headers):
        resp = client.get("/api/v1/intents/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404

    def test_compile_intent(self, client, auth_headers):
        create = client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        intent_id = create.json()["id"]
        resp = client.post(f"/api/v1/intents/{intent_id}/compile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent_id"] == intent_id
        assert data["positive_prompt"]
        assert data["negative_prompt"]
        assert data["cfg_scale"] >= 1.0
        assert data["steps"] >= 10
        assert data["seed"] > 0
        assert len(data["positive_layers"]) >= 3

    def test_compile_is_cached(self, client, auth_headers):
        """Second compile returns cached result without error."""
        create = client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        intent_id = create.json()["id"]
        r1 = client.post(f"/api/v1/intents/{intent_id}/compile", headers=auth_headers)
        r2 = client.post(f"/api/v1/intents/{intent_id}/compile", headers=auth_headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    def test_get_compiled_by_id(self, client, auth_headers):
        create = client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        intent_id = create.json()["id"]
        compiled = client.post(f"/api/v1/intents/{intent_id}/compile", headers=auth_headers)
        compiled_id = compiled.json()["id"]
        resp = client.get(f"/api/v1/intents/compiled/{compiled_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["positive_prompt"] == compiled.json()["positive_prompt"]

    def test_create_intent_preserves_quality(self, client, auth_headers):
        """Quality field is persisted and returned in create/get responses."""
        payload = dict(VALID_PAYLOAD)
        payload["quality"] = "hd"
        resp = client.post("/api/v1/intents/", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["quality"] == "hd"

        # GET should also return the stored quality
        resp2 = client.get(f"/api/v1/intents/{data['id']}", headers=auth_headers)
        assert resp2.status_code == 200
        assert resp2.json()["quality"] == "hd"

    def test_compile_uses_stored_quality(self, client, auth_headers):
        """Compile respects the stored quality (not a hardcoded 'standard')."""
        hd_payload = dict(VALID_PAYLOAD)
        hd_payload["quality"] = "hd"
        std_payload = dict(VALID_PAYLOAD)
        std_payload["quality"] = "standard"
        std_payload["subject"] = "a different subject to avoid seed collision"

        hd_id = client.post("/api/v1/intents/", json=hd_payload, headers=auth_headers).json()["id"]
        std_id = client.post("/api/v1/intents/", json=std_payload, headers=auth_headers).json()["id"]

        hd_compiled = client.post(f"/api/v1/intents/{hd_id}/compile", headers=auth_headers)
        std_compiled = client.post(f"/api/v1/intents/{std_id}/compile", headers=auth_headers)
        assert hd_compiled.status_code == 200
        assert std_compiled.status_code == 200

        hd_data = hd_compiled.json()
        std_data = std_compiled.json()
        # hd has step_mult=1.25 → more steps; cfg_mult=1.1 → higher cfg
        assert hd_data["steps"] > std_data["steps"]
        assert hd_data["cfg_scale"] > std_data["cfg_scale"]



class TestPaginationAndFiltering:
    """Pagination and filtering parameters on list endpoint."""

    def test_pagination(self, client, auth_headers):
        for _ in range(5):
            client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/v1/intents/?per_page=2&page=1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["per_page"] == 2
        assert data["page"] == 1
        assert len(data["intents"]) <= 2
        assert data["has_next"] is True

    def test_filter_by_archetype(self, client, auth_headers):
        payload2 = dict(VALID_PAYLOAD)
        payload2["style_archetype"] = "mythic-landscape"
        client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=auth_headers)
        client.post("/api/v1/intents/", json=payload2, headers=auth_headers)
        resp = client.get(
            "/api/v1/intents/?style_archetype=cinematic-portrait", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(i["style_archetype"] == "cinematic-portrait" for i in data["intents"])


class TestMalformedInput:
    """Malformed and invalid input must be rejected with 422 or 400."""

    def test_extra_fields_rejected(self, client, auth_headers):
        payload = dict(VALID_PAYLOAD)
        payload["unknown_field"] = "hacker"
        resp = client.post("/api/v1/intents/", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_archetype_rejected(self, client, auth_headers):
        payload = dict(VALID_PAYLOAD)
        payload["style_archetype"] = "not-a-real-archetype"
        resp = client.post("/api/v1/intents/", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_mood_rejected(self, client, auth_headers):
        payload = dict(VALID_PAYLOAD)
        payload["mood"] = "nonexistent-mood"
        resp = client.post("/api/v1/intents/", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_empty_subject_rejected(self, client, auth_headers):
        payload = dict(VALID_PAYLOAD)
        payload["subject"] = ""
        resp = client.post("/api/v1/intents/", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_bad_resolution_rejected(self, client, auth_headers):
        payload = dict(VALID_PAYLOAD)
        payload["resolution_w"] = 100  # not multiple of 64
        resp = client.post("/api/v1/intents/", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_resolution_too_large_rejected(self, client, auth_headers):
        payload = dict(VALID_PAYLOAD)
        payload["resolution_w"] = 5000
        payload["resolution_h"] = 5000
        resp = client.post("/api/v1/intents/", json=payload, headers=auth_headers)
        assert resp.status_code == 422


class TestEvaluationEndpoint:
    """The deterministic evaluation endpoint must return metrics."""

    def test_run_evaluation(self, client, auth_headers):
        resp = client.post("/api/v1/evaluation/run", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        metrics = data["metrics"]
        assert metrics["constraint_satisfaction_percent"] == 100.0
        assert metrics["determinism_pass_percent"] == 100.0

    def test_archetypes_endpoint(self, client):
        resp = client.get("/api/v1/evaluation/archetypes")
        assert resp.status_code == 200
        data = resp.json()
        assert "cinematic-portrait" in data["style_archetypes"]
        assert "dramatic" in data["moods"]


class TestAuthBoundary:
    """Auth requirements on all endpoints."""

    def test_health_no_auth(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_intents_list_requires_auth(self, client):
        resp = client.get("/api/v1/intents/")
        assert resp.status_code == 401

    def test_intents_create_requires_auth(self, client):
        resp = client.post("/api/v1/intents/", json=VALID_PAYLOAD)
        assert resp.status_code == 401

    def test_intents_create_requires_operator(self, client, viewer_headers):
        resp = client.post("/api/v1/intents/", json=VALID_PAYLOAD, headers=viewer_headers)
        assert resp.status_code == 403

    def test_audit_requires_admin(self, client, auth_headers):
        resp = client.get("/api/v1/audit/", headers=auth_headers)
        assert resp.status_code == 403

    def test_demo_login_returns_token(self, client):
        resp = client.post(
            "/api/v1/auth/demo-login",
            params={"role": "operator"},
            headers={"host": "127.0.0.1:8000", "x-forwarded-for": "127.0.0.1"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert resp.json()["token_type"] == "bearer"