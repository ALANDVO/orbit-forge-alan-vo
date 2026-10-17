"""Deterministic AI/ML evaluation benchmark suite.

Provides a standardized dataset of creative intents spanning multiple
archetypes, a reproducible evaluation runner, and metric computation.
All evaluations are deterministic and require no LLM key or network access.
"""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from app.models.domain import IntentDefinition
from app.services.intent_engine import (
    ARCHETYPES,
    MOODS,
    LIGHTING,
    COMPOSITIONS,
    IntentEngine,
)

# ---------------------------------------------------------------------------
# Benchmark dataset — five creative archetypes with known expected tokens.
# ---------------------------------------------------------------------------

BENCHMARK_INTENTS: list[IntentDefinition] = [
    IntentDefinition(
        style_archetype="cinematic-portrait",
        subject="a woman with freckles wearing a leather jacket",
        mood="dramatic",
        lighting="three-point-studio",
        composition="close-up",
        quality="standard",
    ),
    IntentDefinition(
        style_archetype="hard-surface-mecha",
        subject="sleek battle-ready mech suit with angular panels",
        mood="energetic",
        lighting="volumetric",
        composition="wide-shot",
        quality="hd",
    ),
    IntentDefinition(
        style_archetype="mythic-landscape",
        subject="floating islands with waterfalls under a twin-moon sky",
        mood="mysterious",
        lighting="golden-hour",
        composition="wide-shot",
        quality="uhd",
    ),
    IntentDefinition(
        style_archetype="aged-wood-pbr",
        subject="weathered oak planks with deep grain and scratches",
        mood="melancholic",
        lighting="overcast-diffuse",
        composition="macro",
        quality="standard",
    ),
    IntentDefinition(
        style_archetype="weathered-iron-pbr",
        subject="cast iron gate with rust stains and oxidation patina",
        mood="mysterious",
        lighting="volumetric",
        composition="close-up",
        quality="standard",
    ),
]

# Expected tokens that must appear in the positive prompt for each benchmark.
BENCHMARK_EXPECTED_TOKENS: list[list[str]] = [
    ["high quality photograph", "cinematic lighting", "rim light", "close up"],
    ["hard surface mech design", "dynamic motion", "volumetric lighting", "wide angle"],
    ["epic landscape", "volumetric lighting", "golden hour", "wide angle"],
    ["aged wood texture", "cool tones", "overcast sky", "macro photography"],
    ["weathered cast iron", "misty", "volumetric lighting", "close up"],
]


class EvaluationMetrics:
    """Container for evaluation results."""

    def __init__(self) -> None:
        self.total_intents: int = 0
        self.constraint_satisfied: int = 0
        self.latencies_ms: list[float] = []
        self.determinism_pass: int = 0

    def to_dict(self) -> dict[str, Any]:
        lats = self.latencies_ms
        avg_lat = sum(lats) / len(lats) if lats else 0.0
        max_lat = max(lats) if lats else 0.0
        return {
            "total_intents": self.total_intents,
            "constraint_satisfaction_percent": round(
                100.0 * self.constraint_satisfied / max(self.total_intents, 1), 1
            ),
            "determinism_pass_percent": round(
                100.0 * self.determinism_pass / max(self.total_intents, 1), 1
            ),
            "mean_latency_ms": round(avg_lat, 2),
            "max_latency_ms": round(max_lat, 2),
        }


def run_evaluation(engine: IntentEngine | None = None) -> dict[str, Any]:
    """Execute the full benchmark suite and return metrics.

    Measures:
    * **Constraint satisfaction**: percentage of benchmark intents whose
      compiled positive prompt contains all expected tokens.
    * **Determinism**: percentage of intents that produce byte-identical
      output when compiled twice (proving reproducibility).
    * **Latency**: mean and max compilation time in milliseconds.
    """
    engine = engine or IntentEngine()
    metrics = EvaluationMetrics()
    metrics.total_intents = len(BENCHMARK_INTENTS)

    for i, intent in enumerate(BENCHMARK_INTENTS):
        expected = BENCHMARK_EXPECTED_TOKENS[i]

        # First compilation
        t0 = time.perf_counter()
        compiled = engine.compile(intent)
        t1 = time.perf_counter()
        metrics.latencies_ms.append((t1 - t0) * 1000.0)

        # Check constraint satisfaction
        pos_lower = compiled.positive_prompt.lower()
        if all(tok.lower() in pos_lower for tok in expected):
            metrics.constraint_satisfied += 1

        # Determinism check: compile again and compare
        compiled2 = engine.compile(intent)
        if (
            compiled.positive_prompt == compiled2.positive_prompt
            and compiled.negative_prompt == compiled2.negative_prompt
            and compiled.cfg_scale == compiled2.cfg_scale
            and compiled.steps == compiled2.steps
            and compiled.seed == compiled2.seed
        ):
            metrics.determinism_pass += 1

    return metrics.to_dict()


def list_benchmark_intents() -> list[dict[str, Any]]:
    """Return benchmark intents as dicts for API display."""
    return [asdict(i) for i in BENCHMARK_INTENTS]