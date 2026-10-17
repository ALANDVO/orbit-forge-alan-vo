import React, { useEffect, useState } from "react";
import { useAuth } from "../services/auth";
import {
  listIntents,
  createIntent,
  deleteIntent,
  fetchArchetypes,
} from "../services/api";
import type {
  PaginatedIntents,
  IntentSchema,
  IntentCreateSchema,
  ArchetypeOptions,
} from "../services/api";
import IntentForm from "./IntentForm";
import IntentDetail from "./IntentDetail";
import LoadingState from "./LoadingState";
import ErrorMessage from "./ErrorMessage";
import EmptyState from "./EmptyState";
import "../components.css";

export default function IntentDashboard(): React.ReactElement {
  const { authenticated } = useAuth();
  const [data, setData] = useState<PaginatedIntents | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [archetypes, setArchetypes] = useState<ArchetypeOptions | null>(null);
  const [selectedIntent, setSelectedIntent] = useState<IntentSchema | null>(null);
  const [showForm, setShowForm] = useState(false);

  const loadIntents = async (refresh = false) => {
    if (refresh) setLoading(true);
    try {
      const result = await listIntents(1, 20);
      setData(result);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const loadArchetypes = async () => {
    try {
      const opts = await fetchArchetypes();
      setArchetypes(opts);
    } catch {
      // Optional — form will use its own defaults
    }
  };

  useEffect(() => {
    if (!authenticated) {
      setLoading(false);
      return;
    }
    loadIntents();
    loadArchetypes();
  }, [authenticated]);

  const handleCreate = async (payload: IntentCreateSchema) => {
    try {
      const intent = await createIntent(payload);
      setShowForm(false);
      await loadIntents(true);
      setSelectedIntent(intent);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this intent?")) return;
    try {
      await deleteIntent(id);
      if (selectedIntent?.id === id) setSelectedIntent(null);
      await loadIntents(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  if (!authenticated) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🔒</div>
        <h3 className="empty-title">Authentication required</h3>
        <p className="empty-description">
          Use the demo login button in the header to start creating intents.
        </p>
      </div>
    );
  }

  if (showForm) {
    return (
      <IntentForm
        archetypes={archetypes}
        onSubmit={handleCreate}
        onCancel={() => setShowForm(false)}
      />
    );
  }

  if (selectedIntent) {
    return (
      <IntentDetail
        intent={selectedIntent}
        onBack={() => setSelectedIntent(null)}
        onRefetch={loadIntents}
      />
    );
  }

  if (loading) {
    return <LoadingState message="Loading intents…" />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => loadIntents(true)} />;
  }

  if (!data || data.intents.length === 0) {
    return (
      <EmptyState
        title="No intents yet"
        description="Create your first intent to generate a deterministic prompt hierarchy."
        actionLabel="Create Intent"
        onAction={() => setShowForm(true)}
      />
    );
  }

  return (
    <div>
      <div className="dashboard-header">
        <h1 className="dashboard-title">Intents</h1>
        <div className="dashboard-filters">
          <button
            className="btn btn-primary"
            onClick={() => setShowForm(true)}
          >
            + New Intent
          </button>
        </div>
      </div>

      <p className="dashboard-meta">
        {data.total} total intent{data.total !== 1 ? "s" : ""}
      </p>

      {data.intents.map((intent) => (
        <div
          key={intent.id}
          className="intent-card"
          onClick={() => setSelectedIntent(intent)}
        >
          <div className="intent-card-header">
            <div>
              <div className="intent-card-title">{intent.subject}</div>
              <div className="intent-card-meta">
                <span className="intent-card-archetype">{intent.style_archetype}</span>
                <span>{intent.mood}</span>
                <span>{intent.lighting}</span>
                <span>{intent.composition}</span>
              </div>
            </div>
            <div className="intent-card-actions">
              {data.compiled[intent.id] && (
                <span className="intent-btn">Compiled</span>
              )}
              <button
                className="intent-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(intent.id);
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      ))}

      {data.has_next && (
        <div className="pagination">
          <button className="btn btn-secondary" onClick={() => loadIntents(true)}>
            Load more
          </button>
        </div>
      )}
    </div>
  );
}