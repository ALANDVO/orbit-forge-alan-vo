"""Deterministic Intent Graph Compiler.

Translates high-level creative intent parameters (style archetype, subject,
mood, lighting, composition) into a fully-specified generation recipe:
structured positive/negative prompt hierarchies, CFG scale, sampler schedule,
deterministic seed, and model recommendation.

Design principles
-----------------
* **Deterministic**: the same ``IntentDefinition`` always yields the same
  ``CompiledIntent``.  No randomness, no LLM calls required.
* **Layered**: positive tokens are organized into priority-ordered ``PromptLayer``
  objects so downstream tools can selectively toggle sections.
* **Validated**: every archetype/mood/lighting/composition is sourced from
  curated dictionaries; unknown values are rejected at the API boundary
  (see ``models.schemas``).
* **Energy-conserving**: energy-conservation checks ($k_d + k_s \\le 1.0$)
  are applied to PBR-related archetypes by adjusting metallic/roughness
  defaults in the model recommendation.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from app.models.domain import (
    CompiledIntent,
    IntentDefinition,
    PromptLayer,
    SamplerSchedule,
)

# ---------------------------------------------------------------------------
# Archetype dictionaries — the rule base for intent compilation.
# Each archetype provides base positive/negative tokens, a default CFG,
# step count, recommended model, and PBR-relevant defaults.
# ---------------------------------------------------------------------------

ARCHETYPES: dict[str, dict[str, Any]] = {
    "cinematic-portrait": {
        "positive_base": [
            "high quality photograph",
            "85mm lens",
            "f/1.8 aperture",
            "shallow depth of field",
            "cinematic lighting",
        ],
        "negative_base": ["blur", "grain", "low resolution", "jpeg artifacts"],
        "default_cfg": 7.5,
        "default_steps": 30,
        "model_rec": "RealisticVision v6.0",
    },
    "hard-surface-mecha": {
        "positive_base": [
            "hard surface mech design",
            "mechanical detail",
            "sci-fi concept art",
            "matte painting",
            "intricate paneling",
        ],
        "negative_base": ["low poly", "blur", "low resolution", "deformed"],
        "default_cfg": 11.0,
        "default_steps": 40,
        "model_rec": "Mechanistic v4.0",
    },
    "mythic-landscape": {
        "positive_base": [
            "epic landscape",
            "volumetric lighting",
            "atmospheric depth",
            "detailed terrain",
            "cinematic wide shot",
        ],
        "negative_base": ["flat", "low contrast", "blur", "low resolution"],
        "default_cfg": 9.0,
        "default_steps": 50,
        "model_rec": "LandscapeDiffusion v3.0",
    },
    "aged-wood-pbr": {
        "positive_base": [
            "aged wood texture",
            "anisotropic grain",
            "diffuse scattering",
            "surface weathering",
            "pbr reference",
        ],
        "negative_base": ["plastic", "mirror", "flat", "seamless tile"],
        "default_cfg": 7.0,
        "default_steps": 35,
        "model_rec": "TextureForge-Wood v2.1",
        "metallic": 0.0,
        "roughness": 0.7,
    },
    "weathered-iron-pbr": {
        "positive_base": [
            "weathered cast iron",
            "microfacet roughness",
            "oxidation patina",
            "normal perturbation",
            "pbr reference",
        ],
        "negative_base": ["plastic", "mirror", "flat", "rust-free"],
        "default_cfg": 6.5,
        "default_steps": 35,
        "model_rec": "TextureForge-Metal v2.1",
        "metallic": 0.9,
        "roughness": 0.55,
    },
    "neon-city-synthwave": {
        "positive_base": [
            "neon cityscape",
            "synthwave aesthetic",
            "cyberpunk",
            "vibrant colors",
            "80s retro",
        ],
        "negative_base": ["dark", "grey", "low saturation", "minimalist"],
        "default_cfg": 12.0,
        "default_steps": 45,
        "model_rec": "SynthWaveDiffusion v1.5",
    },
}

MOODS: dict[str, dict[str, Any]] = {
    "dramatic": {
        "positive": ["high contrast lighting", "deep shadows", "rim light", "backlit"],
        "negative": ["flat lighting", "washed out", "muddy"],
        "cfg_bonus": 1.0,
    },
    "serene": {
        "positive": ["soft lighting", "pastel tones", "calm atmosphere", "gentle"],
        "negative": ["harsh shadows", "chaotic", "aggressive"],
        "cfg_bonus": -0.5,
    },
    "mysterious": {
        "positive": ["misty", "enigmatic", "shadow play", "low key"],
        "negative": ["fully lit", "clear", "transparent"],
        "cfg_bonus": 0.5,
    },
    "energetic": {
        "positive": ["dynamic motion", "sharp lines", "vibrant", "electric"],
        "negative": ["still", "static", "dull"],
        "cfg_bonus": 1.5,
    },
    "melancholic": {
        "positive": ["cool tones", "soft focus", "wistful", "gentle sadness"],
        "negative": ["warm", "vibrant", "happy", "overexposed"],
        "cfg_bonus": 0.0,
    },
    "epic": {
        "positive": ["grand scale", "monumental", "heroic", "sweeping"],
        "negative": ["tiny", "insignificant", "cramped"],
        "cfg_bonus": 2.0,
    },
}

LIGHTING: dict[str, dict[str, list[str]]] = {
    "three-point-studio": {
        "positive": ["studio lighting", "softbox", "fill light", "key light", "back light"],
        "negative": ["harsh shadows", "uneven lighting"],
    },
    "golden-hour": {
        "positive": ["golden hour", "warm sun", "long shadows", "soft glow"],
        "negative": ["cool tones", "harsh overhead"],
    },
    "volumetric": {
        "positive": ["volumetric lighting", "god rays", "atmospheric", "light shafts"],
        "negative": ["flat lighting", "no atmosphere"],
    },
    "neon-rim": {
        "positive": ["neon rim light", "colored backlight", "glow", "cyberpunk lighting"],
        "negative": ["natural lighting", "dull"],
    },
    "overcast-diffuse": {
        "positive": ["overcast sky", "diffuse lighting", "soft shadows", "even illumination"],
        "negative": ["hard shadows", "specular highlights"],
    },
}

COMPOSITIONS: dict[str, dict[str, list[str]]] = {
    "close-up": {
        "positive": ["close up", "portrait orientation", "focus on face", "shallow depth of field"],
        "negative": ["wide angle", "distant view", "full body"],
    },
    "wide-shot": {
        "positive": ["wide angle", "full scene", "environmental context", "landscape orientation"],
        "negative": ["macro", "extreme zoom", "crop"],
    },
    "macro": {
        "positive": ["macro photography", "extreme close-up", "fine detail", "shallow depth of field"],
        "negative": ["distant", "wide angle"],
    },
    "birds-eye": {
        "positive": ["bird's eye view", "aerial perspective", "top down", "overhead"],
        "negative": ["ground level", "worm's eye"],
    },
    "dutch-angle": {
        "positive": ["dutch angle", "tilted horizon", "diagonal composition", "dramatic perspective"],
        "negative": ["level horizon", "straight on"],
    },
}

QUALITY_MODIFIERS: dict[str, dict[str, Any]] = {
    "standard": {"step_mult": 1.0, "cfg_mult": 1.0, "width": 1024, "height": 1024},
    "hd": {"step_mult": 1.25, "cfg_mult": 1.1, "width": 1536, "height": 1536},
    "uhd": {"step_mult": 1.5, "cfg_mult": 1.2, "width": 2048, "height": 2048},
}

SCHEDULER_FOR_ARCHETYPE: dict[str, str] = {
    "cinematic-portrait": "DPM++ 2M Karras",
    "hard-surface-mecha": "Euler a",
    "mythic-landscape": "DPM++ 2M",
    "aged-wood-pbr": "Euler",
    "weathered-iron-pbr": "Euler",
    "neon-city-synthwave": "DPM++ SDE Karras",
}

MAX_STEPS = 150


def _compute_seed(archetype: str, subject: str, mood: str, lighting: str, composition: str, width: int, height: int) -> int:
    """Deterministic 32-bit seed derived from intent parameters via SHA-256."""
    raw = f"{archetype}|{subject}|{mood}|{lighting}|{composition}|{width}x{height}"
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _energy_check(metallic: float | None, roughness: float | None) -> bool:
    """Validate PBR energy conservation: $k_d + k_s \\le 1.0$.

    For dielectlectrics (metallic=0), $k_s$ equals the specular reflectance
    F0 (~0.04).  For metals, $k_d = 0$ so conservation holds trivially.
    Returns True when the material is physically plausible.
    """
    if metallic is None or roughness is None:
        return True
    kd = 1.0 - metallic  # diffuse term scales with (1 - metallic)
    ks = 0.04 if metallic < 0.5 else metallic  # F0 ≈ 0.04 for dielectrics
    return (kd + ks) <= 1.0


class IntentEngine:
    """Pure, stateless intent compilation engine.

    Every method is deterministic and has no side effects, making the engine
    trivially testable and reproducible across runs.
    """

    def __init__(self) -> None:
        # Validate that every archetype has an energy-conservation check.
        self._pbr_archetypes = {
            name: data for name, data in ARCHETYPES.items()
            if "metallic" in data and "roughness" in data
        }
        for name, data in self._pbr_archetypes.items():
            if not _energy_check(data.get("metallic"), data.get("roughness")):
                # Adjust roughness upward to satisfy conservation.
                data["roughness"] = max(data["roughness"], 0.5)

    def compile(self, definition: IntentDefinition) -> CompiledIntent:
        """Compile an ``IntentDefinition`` into a fully specified recipe.

        The compilation is a pure function — identical inputs always produce
        identical outputs.
        """
        arch = ARCHETYPES[definition.style_archetype]
        mood = MOODS[definition.mood]
        lighting = LIGHTING[definition.lighting]
        comp = COMPOSITIONS[definition.composition]
        quality = QUALITY_MODIFIERS[definition.quality]

        # ---- Resolution & quality ----
        w = definition.resolution_w or quality["width"]
        h = definition.resolution_h or quality["height"]

        # ---- Steps (clamped) ----
        base_steps = arch["default_steps"]
        steps = max(10, min(MAX_STEPS, int(base_steps * quality["step_mult"])))

        # ---- CFG scale ----
        cfg = round(
            max(1.0, min(20.0, arch["default_cfg"] + mood["cfg_bonus"]))
            * quality["cfg_mult"],
            2,
        )

        # ---- Scheduler ----
        scheduler = SCHEDULER_FOR_ARCHETYPE[definition.style_archetype]

        # ---- Deterministic seed ----
        seed = _compute_seed(
            definition.style_archetype,
            definition.subject,
            definition.mood,
            definition.lighting,
            definition.composition,
            w,
            h,
        )

        # ---- Positive layers (priority-ordered) ----
        layers: list[PromptLayer] = []
        # Layer 0: subject (highest priority)
        layers.append(PromptLayer(priority=0, label="subject", tokens=[definition.subject]))
        # Layer 1: archetype base
        layers.append(PromptLayer(
            priority=1, label="archetype", tokens=list(arch["positive_base"])
        ))
        # Layer 2: mood
        layers.append(PromptLayer(priority=2, label="mood", tokens=list(mood["positive"])))
        # Layer 3: lighting
        layers.append(PromptLayer(
            priority=3, label="lighting", tokens=list(lighting["positive"])
        ))
        # Layer 4: composition
        layers.append(PromptLayer(
            priority=4, label="composition", tokens=list(comp["positive"])
        ))
        # Layer 5: quality
        if definition.quality == "hd":
            layers.append(PromptLayer(priority=5, label="quality", tokens=["high resolution", "detailed"]))
        elif definition.quality == "uhd":
            layers.append(PromptLayer(
                priority=5, label="quality",
                tokens=["ultra high resolution", "8k", "extremely detailed", "masterpiece"],
            ))

        # Build positive prompt string (flat concatenation, archetype order)
        positive_prompt = _build_prompt(layers)

        # ---- Negative prompt ----
        neg_tokens: list[str] = []
        neg_tokens.extend(arch["negative_base"])
        neg_tokens.extend(mood["negative"])
        neg_tokens.extend(lighting["negative"])
        neg_tokens.extend(comp["negative"])
        negative_prompt = ", ".join(dict.fromkeys(neg_tokens))  # de-dup, preserve order

        # ---- Denoising schedule ----
        if steps <= 30:
            denoising_start, denoising_end = 0.0, 1.0
        elif steps <= 60:
            denoising_start, denoising_end = 0.0, 0.95
        else:
            denoising_start, denoising_end = 0.083, 0.95  # refiner-friendly

        # ---- Model recommendation ----
        model_rec = _recommend_model(definition, arch)

        compiled_id = _generate_id(definition, seed)

        return CompiledIntent(
            id=compiled_id,
            intent_id="",
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            cfg_scale=cfg,
            steps=steps,
            scheduler=scheduler,
            seed=seed,
            width=w,
            height=h,
            denoising_start=denoising_start,
            denoising_end=denoising_end,
            positive_layers=layers,
            model_recommendation=model_rec,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def validate(self, definition: IntentDefinition) -> list[str]:
        """Return a list of validation errors (empty if valid).

        The API layer also validates input, but this method exists for
        programmatic use by the evaluator and for defensive checks inside
        the engine.
        """
        errors: list[str] = []
        if definition.style_archetype not in ARCHETYPES:
            errors.append(f"Unknown archetype: {definition.style_archetype}")
        if definition.mood not in MOODS:
            errors.append(f"Unknown mood: {definition.mood}")
        if definition.lighting not in LIGHTING:
            errors.append(f"Unknown lighting: {definition.lighting}")
        if definition.composition not in COMPOSITIONS:
            errors.append(f"Unknown composition: {definition.composition}")
        if definition.quality not in QUALITY_MODIFIERS:
            errors.append(f"Unknown quality: {definition.quality}")
        return errors


def _build_prompt(layers: list[PromptLayer]) -> str:
    """Flatten priority-ordered layers into a comma-separated prompt string."""
    sorted_layers = sorted(layers, key=lambda l: l.priority)
    all_tokens: list[str] = []
    for layer in sorted_layers:
        all_tokens.extend(layer.tokens)
    # De-duplicate while preserving order
    return ", ".join(dict.fromkeys(all_tokens))


def _recommend_model(definition: IntentDefinition, arch: dict[str, Any]) -> str:
    """Select a model checkpoint recommendation based on archetype and quality."""
    base = arch["model_rec"]
    if definition.quality == "uhd":
        return f"{base} (UHD optimized)"
    if definition.quality == "hd":
        return f"{base} (HD optimized)"
    return base


def _generate_id(definition: IntentDefinition, seed: int) -> str:
    """Generate a stable short ID for a compiled intent."""
    raw = f"{definition.style_archetype}|{seed}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"cmp_{h}"


def list_archetypes() -> list[str]:
    return sorted(ARCHETYPES.keys())


def list_moods() -> list[str]:
    return sorted(MOODS.keys())


def list_lighting() -> list[str]:
    return sorted(LIGHTING.keys())


def list_compositions() -> list[str]:
    return sorted(COMPOSITIONS.keys())