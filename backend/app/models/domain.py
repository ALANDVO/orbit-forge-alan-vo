"""Domain types for intent definitions and compiled results.

These dataclasses represent the internal domain objects used by the intent
engine, decoupled from the persistence layer and API schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptLayer:
    """A single semantically labeled layer of the positive prompt hierarchy."""

    priority: int       # lower = evaluated first
    label: str          # human-readable section name
    tokens: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SamplerSchedule:
    """Deterministic latent sampling parameters."""

    steps: int
    cfg_scale: float
    scheduler: str
    seed: int
    width: int
    height: int
    denoising_start: float
    denoising_end: float


@dataclass(frozen=True)
class IntentDefinition:
    """High-level creative intent input from the user."""

    style_archetype: str
    subject: str
    mood: str
    lighting: str
    composition: str
    resolution_w: int | None = None
    resolution_h: int | None = None
    quality: str | None = None  # "standard" | "hd" | "uhd"


@dataclass(frozen=True)
class CompiledIntent:
    """Complete deterministic compilation result.

    Every field is a pure function of the originating ``IntentDefinition``,
    ensuring reproducibility: the same input always yields the same output.
    """

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
    positive_layers: list[PromptLayer]
    model_recommendation: str
    created_at: str


@dataclass(frozen=True)
class IntentRecord:
    """Intent as persisted in SQLite (subset of CompiledIntent)."""

    id: str
    style_archetype: str
    subject: str
    mood: str
    lighting: str
    composition: str
    resolution_w: int | None
    resolution_h: int | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AuditEntry:
    """A single audit log row."""

    id: int
    timestamp: str
    actor: str
    role: str
    action: str
    resource: str
    resource_id: str | None
    detail: dict[str, Any]