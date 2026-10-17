"""Structured audit logging for all data mutations and privileged reads.

Audit entries are written to the same SQLite database in a separate
``audit_log`` table and are never rolled back when the parent transaction
succeeds.  Each entry records the UTC timestamp, actor identifier, role,
action, resource type, resource id, and a JSON detail blob.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.database import get_db


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_action(
    actor: str,
    role: str,
    action: str,
    resource: str,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Write an immutable audit entry.

    Uses a short-lived connection so the audit write commits independently
    of the caller's transaction, preserving traceability even when the
    triggering operation is later rolled back.
    """
    entry = {
        "timestamp": _utc_now(),
        "actor": actor,
        "role": role,
        "action": action,
        "resource": resource,
        "resource_id": resource_id or "",
        "detail": json.dumps(detail or {}),
    }
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO audit_log
                (timestamp, actor, role, action, resource, resource_id, detail)
            VALUES
                (:timestamp, :actor, :role, :action, :resource, :resource_id, :detail)
            """,
            entry,
        )