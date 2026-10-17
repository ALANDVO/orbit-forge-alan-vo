import React, { useState } from "react";
import type { IntentCreateSchema, ArchetypeOptions } from "../services/api";
import "../components.css";

interface IntentFormProps {
  archetypes: ArchetypeOptions | null;
  onSubmit: (payload: IntentCreateSchema) => Promise<void>;
  onCancel: () => void;
}

const DEFAULT_ARCHETYPES: ArchetypeOptions = {
  style_archetypes: [
    "cinematic-portrait",
    "hard-surface-mecha",
    "mythic-landscape",
    "aged-wood-pbr",
    "weathered-iron-pbr",
    "neon-city-synthwave",
  ],
  moods: ["dramatic", "serene", "mysterious", "energetic", "melancholic", "epic"],
  lighting: [
    "three-point-studio",
    "golden-hour",
    "volumetric",
    "neon-rim",
    "overcast-diffuse",
  ],
  compositions: ["close-up", "wide-shot", "macro", "birds-eye", "dutch-angle"],
};

export default function IntentForm({
  archetypes,
  onSubmit,
  onCancel,
}: IntentFormProps): React.ReactElement {
  const opts = archetypes || DEFAULT_ARCHETYPES;
  const [subject, setSubject] = useState("");
  const [styleArchetype, setStyleArchetype] = useState(opts.style_archetypes[0]);
  const [mood, setMood] = useState(opts.moods[0]);
  const [lighting, setLighting] = useState(opts.lighting[0]);
  const [composition, setComposition] = useState(opts.compositions[0]);
  const [quality, setQuality] = useState<"standard" | "hd" | "uhd">("standard");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim()) {
      setError("Subject is required");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        style_archetype: styleArchetype,
        subject: subject.trim(),
        mood,
        lighting,
        composition,
        quality,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="intent-form" onSubmit={handleSubmit}>
      <h2 className="form-title">Create Intent</h2>

      <div className="form-grid">
        <div className="form-group-full">
          <label className="form-label">Subject</label>
          <input
            className="form-input"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. A woman with freckles wearing a leather jacket"
            maxLength={512}
            required
          />
        </div>

        <div>
          <label className="form-label">Style Archetype</label>
          <select
            className="form-input"
            value={styleArchetype}
            onChange={(e) => setStyleArchetype(e.target.value)}
          >
            {opts.style_archetypes.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="form-label">Mood</label>
          <select className="form-input" value={mood} onChange={(e) => setMood(e.target.value)}>
            {opts.moods.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="form-label">Lighting</label>
          <select
            className="form-input"
            value={lighting}
            onChange={(e) => setLighting(e.target.value)}
          >
            {opts.lighting.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="form-label">Composition</label>
          <select
            className="form-input"
            value={composition}
            onChange={(e) => setComposition(e.target.value)}
          >
            {opts.compositions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="form-label">Quality</label>
          <select
            className="form-input"
            value={quality}
            onChange={(e) => setQuality(e.target.value as typeof quality)}
          >
            <option value="standard">Standard (1024px)</option>
            <option value="hd">HD (1536px)</option>
            <option value="uhd">UHD (2048px)</option>
          </select>
        </div>
      </div>

      {error && <div className="error-message" style={{ marginTop: "1rem" }}>{error}</div>}

      <div className="form-actions">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
        >
          {submitting ? "Creating…" : "Create Intent"}
        </button>
      </div>
    </form>
  );
}