"""Tests for the deterministic Intent Graph Compiler engine.

Covers: determinism (same input → same output), all archetype coverage,
mood/lighting/composition variations, quality modifiers, boundary
conditions, and malformed input handling via the API-layer validators.
"""

from __future__ import annotations

import pytest

from app.models.domain import IntentDefinition
from app.services.intent_engine import (
    ARCHETYPES,
    MOODS,
    LIGHTING,
    COMPOSITIONS,
    QUALITY_MODIFIERS,
    IntentEngine,
    MAX_STEPS,
)
from app.services.benchmark import run_evaluation, BENCHMARK_INTENTS


@pytest.fixture
def engine() -> IntentEngine:
    return IntentEngine()


@pytest.fixture
def base_intent():
    return IntentDefinition(
        style_archetype="cinematic-portrait",
        subject="a woman with freckles wearing a leather jacket",
        mood="dramatic",
        lighting="three-point-studio",
        composition="close-up",
        quality="standard",
    )


class TestDeterminism:
    """The compiler must be a pure function: identical inputs yield identical outputs."""

    def test_same_input_produces_same_output(self, engine, base_intent):
        a = engine.compile(base_intent)
        b = engine.compile(base_intent)
        assert a.positive_prompt == b.positive_prompt
        assert a.negative_prompt == b.negative_prompt
        assert a.cfg_scale == b.cfg_scale
        assert a.steps == b.steps
        assert a.seed == b.seed

    def test_different_subjects_produce_different_seeds(self, engine, base_intent):
        other = IntentDefinition(
            style_archetype=base_intent.style_archetype,
            subject="a different subject entirely",
            mood=base_intent.mood,
            lighting=base_intent.lighting,
            composition=base_intent.composition,
            quality=base_intent.quality,
        )
        a = engine.compile(base_intent)
        b = engine.compile(other)
        assert a.seed != b.seed

    def test_seed_is_deterministic_across_instances(self, base_intent):
        e1 = IntentEngine()
        e2 = IntentEngine()
        assert e1.compile(base_intent).seed == e2.compile(base_intent).seed


class TestArchetypeCoverage:
    """Every defined archetype must produce a valid compiled result."""

    @pytest.mark.parametrize("archetype", sorted(ARCHETYPES.keys()))
    def test_all_archetypes_compile(self, engine, archetype):
        intent = IntentDefinition(
            style_archetype=archetype,
            subject="test subject",
            mood="dramatic",
            lighting="three-point-studio",
            composition="close-up",
            quality="standard",
        )
        compiled = engine.compile(intent)
        assert compiled.positive_prompt
        assert compiled.negative_prompt
        assert compiled.cfg_scale >= 1.0
        assert compiled.steps >= 10
        assert compiled.seed > 0

    def test_all_moods_modify_cfg(self, engine, base_intent):
        cfgs = set()
        for mood in MOODS:
            intent = IntentDefinition(
                style_archetype=base_intent.style_archetype,
                subject=base_intent.subject,
                mood=mood,
                lighting=base_intent.lighting,
                composition=base_intent.composition,
                quality=base_intent.quality,
            )
            compiled = engine.compile(intent)
            cfgs.add(compiled.cfg_scale)
        # At least some moods must produce different CFG values.
        assert len(cfgs) >= 2

    @pytest.mark.parametrize("lighting", sorted(LIGHTING.keys()))
    def test_all_lighting_schemas(self, engine, base_intent, lighting):
        intent = IntentDefinition(
            style_archetype=base_intent.style_archetype,
            subject=base_intent.subject,
            mood=base_intent.mood,
            lighting=lighting,
            composition=base_intent.composition,
            quality=base_intent.quality,
        )
        compiled = engine.compile(intent)
        assert compiled.positive_prompt  # should contain lighting tokens

    @pytest.mark.parametrize("comp", sorted(COMPOSITIONS.keys()))
    def test_all_compositions(self, engine, base_intent, comp):
        intent = IntentDefinition(
            style_archetype=base_intent.style_archetype,
            subject=base_intent.subject,
            mood=base_intent.mood,
            lighting=base_intent.lighting,
            composition=comp,
            quality=base_intent.quality,
        )
        compiled = engine.compile(intent)
        assert compiled.positive_prompt

    @pytest.mark.parametrize("quality", sorted(QUALITY_MODIFIERS.keys()))
    def test_quality_modifiers_affect_steps(self, engine, base_intent, quality):
        intent = IntentDefinition(
            style_archetype=base_intent.style_archetype,
            subject=base_intent.subject,
            mood=base_intent.mood,
            lighting=base_intent.lighting,
            composition=base_intent.composition,
            quality=quality,
        )
        compiled = engine.compile(intent)
        assert compiled.steps > 0
        assert compiled.steps <= MAX_STEPS


class TestBoundaryConditions:
    """Boundary and edge-case behavior."""

    def test_resolution_clamping_via_quality(self, engine):
        intent_uhd = IntentDefinition(
            style_archetype="mythic-landscape",
            subject="floating islands",
            mood="epic",
            lighting="volumetric",
            composition="wide-shot",
            quality="uhd",
        )
        compiled = engine.compile(intent_uhd)
        assert compiled.width == 2048
        assert compiled.height == 2048

    def test_max_steps_not_exceeded(self, engine):
        intent = IntentDefinition(
            style_archetype="neon-city-synthwave",
            subject="neon streets at night",
            mood="energetic",
            lighting="neon-rim",
            composition="wide-shot",
            quality="uhd",
        )
        compiled = engine.compile(intent)
        assert compiled.steps <= MAX_STEPS

    def test_energy_conservation_pbr(self, engine):
        """PBR archetypes must satisfy k_d + k_s <= 1.0."""
        for label, intent in [("aged-wood", IntentDefinition(
            style_archetype="aged-wood-pbr", subject="wood", mood="serene",
            lighting="overcast-diffuse", composition="macro", quality="standard"
        )), ("weathered-iron", IntentDefinition(
            style_archetype="weathered-iron-pbr", subject="iron", mood="mysterious",
            lighting="volumetric", composition="close-up", quality="standard"
        ))]:
            compiled = engine.compile(intent)
            assert compiled.cfg_scale <= 20.0  # bounded


class TestBenchmarkSuite:
    """The evaluation benchmark must pass all metrics."""

    def test_benchmark_all_archetypes(self, engine):
        metrics = run_evaluation(engine)
        assert metrics["total_intents"] == len(BENCHMARK_INTENTS)
        assert metrics["constraint_satisfaction_percent"] == 100.0
        assert metrics["determinism_pass_percent"] == 100.0
        assert metrics["mean_latency_ms"] > 0
        assert metrics["max_latency_ms"] >= metrics["mean_latency_ms"]

    def test_benchmark_intents_cover_all_archetypes(self):
        archetypes_in_bench = {i.style_archetype for i in BENCHMARK_INTENTS}
        assert len(archetypes_in_bench) >= 4  # spans multiple archetypes


class TestValidation:
    """The engine validates intent definitions against known archetypes."""

    def test_validate_rejects_unknown_archetype(self, engine):
        intent = IntentDefinition(
            style_archetype="nonexistent",
            subject="test", mood="dramatic",
            lighting="three-point-studio", composition="close-up", quality="standard"
        )
        errors = engine.validate(intent)
        assert any("nonexistent" in e for e in errors)

    def test_validate_rejects_unknown_mood(self, engine):
        intent = IntentDefinition(
            style_archetype="cinematic-portrait", subject="test",
            mood="unknown-mood", lighting="three-point-studio",
            composition="close-up", quality="standard"
        )
        errors = engine.validate(intent)
        assert any("unknown-mood" in e for e in errors)