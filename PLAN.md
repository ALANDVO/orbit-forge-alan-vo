# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

intent-crafting-engine

## Roadmap

### intent-crafting-engine — Intent-driven multi-modal prompt graph synthesis and local pipeline generator

Status: done

Acceptance:
- Deterministic intent compilation translating high-level aesthetic goals into multi-stage generation recipes
- Local ComfyUI/Diffusers compatible execution graph builder and PBR texture map parameter synthesis
- REST API endpoints with SQLite persistence, pagination, filtering, audit logging, and role-based authorization
- Interactive React studio UI with workflow orchestration, PBR studio, pipeline compiler, and reproducible evaluation panel

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/auth.py`, `backend/app/core/audit.py`, `backend/app/models/schemas.py`, `backend/app/models/domain.py`, `backend/app/services/intent_engine.py`, `backend/app/services/pbr_synthesizer.py`, `backend/app/services/comfy_adapter.py`, `backend/app/services/llm_advisor.py`, `backend/app/services/evaluator.py`, `backend/app/api/auth.py`, `backend/app/api/intents.py`, `backend/app/api/materials.py`, `backend/app/api/pipelines.py`, `backend/app/api/audit.py`, `backend/app/api/evaluation.py`, `frontend/src/App.tsx`, `frontend/src/components/Navbar.tsx`, `frontend/src/components/IntentDashboard.tsx`, `frontend/src/components/PBRMaterialStudio.tsx`, `frontend/src/components/PipelineCompilerView.tsx`, `frontend/src/components/EvaluationPanel.tsx`, `frontend/src/components/AuditLogView.tsx`, `frontend/src/services/api.ts`, `frontend/src/services/auth.ts`

Tests: `backend/tests/test_intent_engine.py`, `backend/tests/test_pbr_synthesizer.py`, `backend/tests/test_comfy_adapter.py`, `backend/tests/test_api_workflows.py`, `backend/tests/test_auth_and_system.py`, `backend/tests/test_llm_advisor.py`, `backend/tests/test_evaluator.py`, `frontend/src/__tests__/App.test.tsx`, `frontend/src/__tests__/PBRMaterialStudio.test.tsx`, `frontend/src/__tests__/PipelineCompilerView.test.tsx`

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

