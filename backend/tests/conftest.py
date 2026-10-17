"""Shared test fixtures for the Orbit Forge backend test suite.

Each test gets a fresh temp-file SQLite database to ensure isolation.
The settings cache and any module-level engine state are reset per test.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure backend package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set defaults before any app import so the module-level get_settings() cache
# picks up test-safe values.
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci")

from app.core.config import Settings, get_settings
from app.core.database import init_db
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path):
    """Return Settings pointing at a fresh temp-file database."""
    db_path = str(tmp_path / "test.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DEMO_MODE"] = "true"
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def app(test_settings):
    """Create a FastAPI test app with initialized schema.

    init_db is idempotent (CREATE TABLE IF NOT EXISTS), so calling it
    here and in the lifespan is safe.
    """
    init_db(test_settings.database_url)
    return create_app(test_settings)


@pytest.fixture
def client(app):
    """FastAPI TestClient — runs the lifespan, so the DB is initialised.

    All requests carry ``x-forwarded-for: 127.0.0.1`` so that demo-mode
    localhost detection works correctly under the test client.
    """
    from fastapi.testclient import TestClient

    with TestClient(app, headers={"x-forwarded-for": "127.0.0.1"}) as c:
        yield c

def _demo_login(client, role: str = "operator"):
    resp = client.post(
        "/api/v1/auth/demo-login",
        params={"role": role},
        headers={"x-forwarded-for": "127.0.0.1"},
    )
    assert resp.status_code == 200, f"demo-login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client) -> dict[str, str]:
    """Operator-level bearer token from demo-login."""
    return _demo_login(client, "operator")


@pytest.fixture
def viewer_headers(client) -> dict[str, str]:
    """Viewer-level bearer token from demo-login."""
    return _demo_login(client, "viewer")


@pytest.fixture
def admin_headers(client) -> dict[str, str]:
    """Admin-level bearer token from demo-login."""
    return _demo_login(client, "admin")