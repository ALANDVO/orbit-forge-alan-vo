import React, { useEffect, useState } from "react";
import type { IntentSchema, CompiledIntentSchema } from "../services/api";
import { compileIntent } from "../services/api";
import LoadingState from "./LoadingState";
import ErrorMessage from "./ErrorMessage";
import "../components.css";

interface IntentDetailProps {
  intent: IntentSchema;
  onBack: () => void;
  onRefetch: () => void;
}

export default function IntentDetail({
  intent,
  onBack,
  onRefetch,
}: IntentDetailProps): React.ReactElement {
  const [compiled, setCompiled] = useState<CompiledIntentSchema | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<"positive" | "negative" | null>(null);

  // Reset compiled state when the selected intent changes.
  useEffect(() => {
    setCompiled(null);
    setError(null);
  }, [intent.id]);

  const handleCompile = async () => {
    setCompiling(true);
    setError(null);
    try {
      const result = await compileIntent(intent.id);
      setCompiled(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCompiling(false);
    }
  };

  const handleCopy = async (type: "positive" | "negative") => {
    if (!compiled) return;
    const text = type === "positive" ? compiled.positive_prompt : compiled.negative_prompt;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(type);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // Clipboard API may fail in some contexts; ignore silently
    }
  };

  const handleCompile = async () => {
    setCompiling(true);
    setError(null);
    try {
      const result = await compileIntent(intent.id);
      setCompiled(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCompiling(false);
    }
  };

  return (
    <div>
      <div className="intent-detail-header">
        <div>
          <button className="back-link" onClick={onBack}>
            ← Back
          </button>
          <h1 className="intent-detail-title">{intent.subject}</h1>
          <div className="intent-detail-meta">
            <span className="intent-card-archetype">{intent.style_archetype}</span>
            <span>{intent.mood}</span>
            <span>{intent.lighting}</span>
            <span>{intent.composition}</span>
          </div>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleCompile}
          disabled={compiling}
        >
          {compiling ? "Compiling…" : compiled ? "Recompile" : "Compile"}
        </button>
      </div>

      {error && <ErrorMessage error={error} onRetry={handleCompile} />}

      {compiled ? (
        <div className="intent-detail">
          <div className="param-grid">
            <div><span className="param-label">CFG Scale</span><span className="param-value">{compiled.cfg_scale}</span></div>
            <div><span className="param-label">Steps</span><span className="param-value">{compiled.steps}</span></div>
            <div><span className="param-label">Scheduler</span><span className="param-value">{compiled.scheduler}</span></div>
            <div><span className="param-label">Seed</span><span className="param-value">{compiled.seed}</span></div>
            <div><span className="param-label">Resolution</span><span className="param-value">{compiled.width}×{compiled.height}</span></div>
            <div><span className="param-label">Model</span><span className="param-value">{compiled.model_recommendation}</span></div>
            <div><span className="param-label">Denoise</span><span className="param-value">{compiled.denoising_start}–{compiled.denoising_end}</span></div>
            <div><span className="param-label">Layers</span><span className="param-value">{compiled.positive_layers.length}</span></div>
          </div>

          <div className="prompt-section">
            <div className="prompt-header">
              <div className="prompt-label">Positive Prompt</div>
              <button
                className="copy-btn"
                onClick={() => handleCopy("positive")}
                disabled={copied === "positive"}
              >
                {copied === "positive" ? "✓ Copied" : "Copy"}
              </button>
            </div>
            <pre className="prompt-text">{compiled.positive_prompt}</pre>
          </div>

          <div className="prompt-section">
            <div className="prompt-header">
              <div className="prompt-label">Negative Prompt</div>
              <button
                className="copy-btn"
                onClick={() => handleCopy("negative")}
                disabled={copied === "negative"}
              >
                {copied === "negative" ? "✓ Copied" : "Copy"}
              </button>
            </div>
            <pre className="prompt-text">{compiled.negative_prompt}</pre>
          </div>

          <div className="prompt-section">
            <div className="prompt-label">Prompt Layers (priority order)</div>
            {compiled.positive_layers
              .slice()
              .sort((a, b) => a.priority - b.priority)
              .map((layer) => (
                <div key={layer.label} className="layer-item">
                  <div className="layer-header">
                    <span className="layer-label">{layer.label}</span>
                    <span className="layer-priority">priority {layer.priority}</span>
                  </div>
                  <div className="layer-tokens">
                    {layer.tokens.map((t) => (
                      <span key={t} className="layer-token">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-icon">⚙</div>
          <h3 className="empty-title">Not yet compiled</h3>
          <p className="empty-description">
            Click the Compile button above to generate the deterministic
            prompt hierarchy.
          </p>
        </div>
      )}
    </div>
  );
}