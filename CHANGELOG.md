# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-12

Authored by Alan Vo <alanvo@gmail.com>.

### Added
- Intent graph synthesis engine translating high-level aesthetic intent (style, mood, subject, lighting, composition) into structured positive and negative prompt hierarchies.
- Deterministic latent sampling configuration, CFG scale calculation, and scheduler parameters.
- Local ComfyUI and Diffusers execution graph builder supporting topological acyclic DAG compilation and local VRAM estimation.
- Procedural PBR material parameter synthesizer computing physical albedo RGB, microfacet roughness, metallic reflectance, normal perturbation, and MaterialX XML specifications.
- Physical energy conservation validation ($k_d + k_s \le 1.0$) ensuring physically plausible materials.
- Pluggable advisory LLM integration supporting OpenAI-compatible, Anthropic, Gemini, and Ollama providers with bounded timeouts and error redaction.
- Reproducible AI/ML evaluation benchmark suite with automated metrics: constraint satisfaction rate, energy conservation adherence, DAG acyclicity, and latency.
- SQLite persistent storage with WAL mode, parameterized queries, pagination, filtering, and audit trail.
- Role-based access control with `viewer`, `operator`, and `admin` roles, JWT token verification, and localhost-only demo mode with production lockout.
- Keycloak realm configuration with PKCE authorization-code flow and enterprise SAML identity brokering architecture.
- React 18 + TypeScript + Vite frontend with responsive dark UI, Intent Dashboard, PBR Studio, Pipeline Compiler, and Evaluation panel.
- Docker containerization for backend and frontend with unprivileged non-root execution.

### Fixed
- `quality` field now persisted in `intents` table schema (was missing column; compile endpoint hardcoded `quality="standard"` ignoring the stored value).
- Frontend IntentDashboard test isolation: added `afterEach(cleanup)` and explicit DOM teardown; RTL auto-cleanup was disabled because vitest config lacked `globals: true`.
- Frontend `tsconfig.json` `lib` updated to `ES2024` to resolve `Promise.withResolvers` type error.
- Frontend test setup replaced manual `expect.extend(matchers)` with `import "@testing-library/jest-dom/vitest"` for proper type augmentation of jest-dom matchers.
- `App.test.tsx` wrapped all renders in `await act(async () => …)` and added `listIntents` mock to flush async `useEffect` calls.
- `IntentDashboard.test.tsx` `renderAndFlush` fixed: `await resolve` (function) replaced with `await promise` (the actual promise from `Promise.withResolvers`).

### Changed
- `IntentSchema` now includes `quality: str` field, serialized in all intent API responses (GET, POST, list).

### Tests
- Added `test_create_intent_preserves_quality`: verifies `quality` is stored and returned in create + GET responses.
- Added `test_compile_uses_stored_quality`: verifies compile produces higher steps and cfg_scale for `"hd"` quality vs `"standard"`.
