/** Typed REST API client for the Orbit Forge backend.

All responses are derived from the actual backend route definitions.
The client reads the auth token from an in-memory store (never localStorage)
and attaches it as a Bearer header on every request.
*/

export interface PromptLayer {
  priority: number;
  label: string;
  tokens: string[];
}

export interface IntentSchema {
  id: string;
  style_archetype: string;
  subject: string;
  mood: string;
  lighting: string;
  composition: string;
  resolution_w: number | null;
  resolution_h: number | null;
  created_at: string;
  updated_at: string;
}

export interface CompiledIntentSchema {
  id: string;
  intent_id: string;
  positive_prompt: string;
  negative_prompt: string;
  cfg_scale: number;
  steps: number;
  scheduler: string;
  seed: number;
  width: number;
  height: number;
  denoising_start: number;
  denoising_end: number;
  positive_layers: PromptLayer[];
  model_recommendation: string;
  created_at: string;
}

export interface PaginatedIntents {
  intents: IntentSchema[];
  compiled: Record<string, CompiledIntentSchema>;
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
}

export interface IntentCreateSchema {
  style_archetype: string;
  subject: string;
  mood: string;
  lighting: string;
  composition: string;
  resolution_w?: number;
  resolution_h?: number;
  quality?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  demo_mode: boolean;
}

export interface AuditEntrySchema {
  id: number;
  timestamp: string;
  actor: string;
  role: string;
  action: string;
  resource: string;
  resource_id: string | null;
  detail: Record<string, unknown>;
}

export interface ArchetypeOptions {
  style_archetypes: string[];
  moods: string[];
  lighting: string[];
  compositions: string[];
}

export interface EvaluationMetrics {
  total_intents: number;
  constraint_satisfaction_percent: number;
  determinism_pass_percent: number;
  mean_latency_ms: number;
  max_latency_ms: number;
}

// --- Token management (in-memory only; never persisted to localStorage) ---

let _token: string | null = null;

export function setToken(token: string | null): void {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

export function clearToken(): void {
  _token = null;
}

// --- Base fetch wrapper ---

const API_BASE = "/api";
const V1 = "/api/v1";

function buildHeaders(init?: RequestInit): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (init?.headers) {
    Object.assign(headers, init.headers);
  }
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }
  return headers;
}

async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const url = input.startsWith("http") ? input : `${API_BASE}${input}`;
  return fetch(url, { ...init, headers: buildHeaders(init) });
}

async function apiJson<T>(input: string, init: RequestInit = {}): Promise<T> {
  const resp = await apiFetch(input, init);
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`API ${resp.status}: ${text || resp.statusText}`);
  }
  return (await resp.json()) as T;
}

// --- Endpoints ---

export async function fetchHealth(): Promise<HealthResponse> {
  return apiJson(`${V1}/health`);
}

export async function demoLogin(
  role: "viewer" | "operator" | "admin" = "operator",
): Promise<TokenResponse> {
  const resp = await apiFetch(`${V1}/auth/demo-login?role=${role}`, {
    method: "POST",
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`Login ${resp.status}: ${text || resp.statusText}`);
  }
  const data = (await resp.json()) as TokenResponse;
  setToken(data.access_token);
  return data;
}

export async function listIntents(
  page = 1,
  perPage = 20,
  archetype?: string,
): Promise<PaginatedIntents> {
  const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
  if (archetype) params.set("style_archetype", archetype);
  return apiJson(`${V1}/intents/?${params}`);
}

export async function createIntent(payload: IntentCreateSchema): Promise<IntentSchema> {
  return apiJson(`${V1}/intents/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getIntent(id: string): Promise<IntentSchema> {
  return apiJson(`${V1}/intents/${id}`);
}

export async function compileIntent(id: string): Promise<CompiledIntentSchema> {
  return apiJson(`${V1}/intents/${id}/compile`, { method: "POST" });
}

export async function getCompiledIntent(id: string): Promise<CompiledIntentSchema> {
  return apiJson(`${V1}/intents/compiled/${id}`);
}

export async function deleteIntent(id: string): Promise<void> {
  await apiFetch(`${V1}/intents/${id}`, { method: "DELETE" });
}

export async function fetchArchetypes(): Promise<ArchetypeOptions> {
  return apiJson(`${V1}/evaluation/archetypes`);
}

export async function runEvaluation(): Promise<{ status: string; metrics: EvaluationMetrics }> {
  return apiJson(`${V1}/evaluation/run`, { method: "POST" });
}

export async function fetchAudit(
  page = 1,
  perPage = 50,
  action?: string,
): Promise<AuditEntrySchema[]> {
  const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
  if (action) params.set("action", action);
  return apiJson(`${V1}/audit/?${params}`);
}