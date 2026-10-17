"""Pydantic request/response schemas with validation constraints.

All schemas use strict typing and validators to reject malformed input at
the API boundary, well before reaching the domain engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Valid enum values (kept as sets for validation; the engine uses them as dict
# keys).
# ---------------------------------------------------------------------------

VALID_ARCHETYPES = {
    "cinematic-portrait",
    "hard-surface-mecha",
    "mythic-landscape",
    "aged-wood-pbr",
    "weathered-iron-pbr",
    "neon-city-synthwave",
}

VALID_MOODS = {
    "dramatic",
    "serene",
    "mysterious",
    "energetic",
    "melancholic",
    "epic",
}

VALID_LIGHTING = {
    "three-point-studio",
    "golden-hour",
    "volumetric",
    "neon-rim",
    "overcast-diffuse",
}

VALID_COMPOSITIONS = {
    "close-up",
    "wide-shot",
    "macro",
    "birds-eye",
    "dutch-angle",
}

VALID_QUALITIES = {"standard", "hd", "uhd"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PromptLayerSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: int
    label: str
    tokens: list[str]


class SamplerScheduleSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: int
    cfg_scale: float
    scheduler: str
    seed: int
    width: int
    height: int
    denoising_start: float
    denoising_end: float


class IntentCreateSchema(BaseModel):
    """Input for creating a new intent."""

    model_config = ConfigDict(extra="forbid")

    style_archetype: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=512)
    mood: str = Field(min_length=1, max_length=32)
    lighting: str = Field(min_length=1, max_length=32)
    composition: str = Field(min_length=1, max_length=32)
    resolution_w: int = Field(default=1024, ge=256, le=4096)
    resolution_h: int = Field(default=1024, ge=256, le=4096)
    quality: str = Field(default="standard", max_length=16)

    @field_validator("style_archetype")
    @classmethod
    def _validate_archetype(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_ARCHETYPES:
            raise ValueError(
                f"Invalid style_archetype: {v!r}. "
                f"Valid: {sorted(VALID_ARCHETYPES)}"
            )
        return v

    @field_validator("mood")
    @classmethod
    def _validate_mood(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_MOODS:
            raise ValueError(
                f"Invalid mood: {v!r}. Valid: {sorted(VALID_MOODS)}"
            )
        return v

    @field_validator("lighting")
    @classmethod
    def _validate_lighting(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_LIGHTING:
            raise ValueError(
                f"Invalid lighting: {v!r}. Valid: {sorted(VALID_LIGHTING)}"
            )
        return v

    @field_validator("composition")
    @classmethod
    def _validate_composition(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_COMPOSITIONS:
            raise ValueError(
                f"Invalid composition: {v!r}. Valid: {sorted(VALID_COMPOSITIONS)}"
            )
        return v

    @field_validator("quality")
    @classmethod
    def _validate_quality(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_QUALITIES:
            raise ValueError(
                f"Invalid quality: {v!r}. Valid: {sorted(VALID_QUALITIES)}"
            )
        return v

    @model_validator(mode="after")
    def _validate_resolution(self) -> "IntentCreateSchema":
        w, h = self.resolution_w, self.resolution_h
        if w % 64 != 0 or h % 64 != 0:
            raise ValueError("Resolution dimensions must be multiples of 64")
        if w * h > 8192 * 8192:
            raise ValueError("Resolution exceeds maximum supported canvas size")
        return self


class IntentSchema(BaseModel):
    """Full intent record returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    style_archetype: str
    subject: str
    mood: str
    lighting: str
    composition: str
    resolution_w: int | None
    resolution_h: int | None
    quality: str
    created_at: str


class CompiledIntentSchema(BaseModel):
    """Compiled intent result returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    intent_id: str
    positive_prompt: str
    negative_prompt: str
    cfg_scale: float
    steps: int
    scheduler: str
    seed: int
    width: int
    height: int
    denoising_start: float
    denoising_end: float
    positive_layers: list[PromptLayerSchema]
    model_recommendation: str
    created_at: str


class PaginatedIntents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intents: list[IntentSchema]
    compiled: dict[str, CompiledIntentSchema]
    total: int
    page: int
    per_page: int
    has_next: bool


class AuditEntrySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    timestamp: str
    actor: str
    role: str
    action: str
    resource: str
    resource_id: str | None
    detail: dict[str, Any]


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800
    role: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    version: str = "1.0.0"
    environment: str = "development"
    demo_mode: bool = False