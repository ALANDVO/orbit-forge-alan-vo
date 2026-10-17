# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

intent-crafting-engine

## Roadmap

### intent-crafting-engine — Deterministic Intent Graph Compiler with SQLite persistence and React studio

Status: in_progress

Acceptance:
- Deterministic intent compilation translating high-level aesthetic goals (style archetype, subject, mood, lighting, composition) into structured positive/negative prompt hierarchies, CFG scale, sampler schedule, and deterministic seed
- SQLite persistence with parameterized queries, pagination, filtering, UTC timestamps, and audit log
- JWT bearer-only auth with localhost-only demo mode and production lockout, viewer/operator/admin role-based authorization on all data endpoints
- REST API endpoints: health, demo-login, intent CRUD, intent compile, audit query
- React + TypeScript studio UI with create intent form, intent dashboard, compiled intent detail view, loading/error/empty states
- Backend pytest suite covering intent engine determinism and boundary/malformed inputs, API create/read workflows, auth rejection/role denial; frontend Vitest tests covering user-visible dashboard behavior

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/auth.py`, `backend/app/core/audit.py`, `backend/app/models/__init__.py`, `backend/app/models/domain.py`, `backend/app/models/schemas.py`, `backend/app/services/__init__.py`, `backend/app/services/intent_engine.py`, `backend/app/services/benchmark.py`, `backend/app/api/__init__.py`, `backend/app/api/auth.py`, `backend/app/api/intents.py`

Tests: `backend/tests/conftest.py`, `backend/tests/test_intent_engine.py`, `backend/tests/test_api_workflows.py`, `backend/tests/test_auth_and_system.py`, `frontend/src/__tests__/App.test.tsx`, `frontend/src/__tests__/IntentDashboard.test.tsx`

### linux-hardware-daemon — Cross-platform hardware detection and AppImage runner daemon

Status: planned

Acceptance:
- Local Linux GPU memory and compute thread monitor
- Subprocess management daemon for headless local model execution
- Safe error recovery on desktop launcher startup

### materialx-pbr-export-viewer — 3D WebGL PBR viewport and MaterialX XML package export

Status: planned

Acceptance:
- Interactive 3D Three.js mesh canvas rendering normal, roughness, metallic, and displacement
- Real-time procedural paint layer preview
- MaterialX XML package export compatible with Blender and Unreal Engine

### keycloak-saml-federation — Keycloak OIDC authentication and enterprise SAML broker integration

Status: planned

Acceptance:
- Production Keycloak OIDC authorization-code exchange with PKCE and state/nonce validation
- SAML identity provider federation via Keycloak realm identity brokering
- Granular viewer/operator/admin role assignments mapped to enterprise directory groups

