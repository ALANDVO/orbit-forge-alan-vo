"""Deterministic evaluation benchmark endpoints.

Triggers the built-in AI/ML evaluation suite — no LLM key or network
required.  Results measure constraint satisfaction, determinism, and
compilation latency across the benchmark dataset.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.auth import User, require_role
from app.services.benchmark import run_evaluation
from app.services.intent_engine import IntentEngine, list_archetypes, list_moods, list_lighting, list_compositions
from app.models.domain import IntentDefinition
from app.services.benchmark import BENCHMARK_INTENTS, list_benchmark_intents

router = APIRouter(tags=["evaluation"])

_engine: IntentEngine | None = None


def _get_engine() -> IntentEngine:
    global _engine
    if _engine is None:
        _engine = IntentEngine()
    return _engine


@router.post("/run")
def run_eval(
    _user: User = Depends(require_role("operator")),
) -> dict[str, Any]:
    """Execute the deterministic benchmark suite and return metrics."""
    engine = _get_engine()
    metrics = run_evaluation(engine)
    return {
        "status": "completed",
        "metrics": metrics,
    }


@router.get("/archetypes")
def get_archetypes() -> dict[str, list[str]]:
    """Return valid enum values for intent compilation."""
    return {
        "style_archetypes": list_archetypes(),
        "moods": list_moods(),
        "lighting": list_lighting(),
        "compositions": list_compositions(),
    }