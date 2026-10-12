# Changelog

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
- Comprehensive automated test suite with pytest backend tests and Vitest frontend integration tests.
