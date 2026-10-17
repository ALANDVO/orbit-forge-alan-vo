"""Audit log query endpoints.

The audit log records every authenticated mutation and privileged read.
Access is restricted to the ``admin`` role per the security contract.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import User, require_role
from app.core.database import fetch_all, get_db
from app.models.schemas import AuditEntrySchema

router = APIRouter(tags=["audit"])


@router.get("/", response_model=list[AuditEntrySchema])
def list_audit(
    page: int = Query(default=1, ge=1, le=10000),
    per_page: int = Query(default=50, ge=1, le=500),
    action: str | None = Query(default=None),
    _user: User = Depends(require_role("admin")),
) -> list[AuditEntrySchema]:
    offset = (page - 1) * per_page
    filters: list[str] = []
    params: list[Any] = [per_page, offset]

    if action is not None:
        filters.append("action = ?")
        params.append(action)

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    query = (
        f"SELECT * FROM audit_log {where_clause} "
        f"ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    )
    # Adjust parameter order: filters first, then LIMIT/OFFSET
    if action is not None:
        limit_offset_params = [params[0], params[1]]
        filter_params = [params[2]]
        final_params = tuple(filter_params + limit_offset_params)
    else:
        final_params = tuple(params)

    with get_db() as conn:
        rows = fetch_all(conn, query, final_params)

    entries: list[AuditEntrySchema] = []
    for row in rows:
        detail_raw = row["detail"]
        if isinstance(detail_raw, str):
            import json
            detail = json.loads(detail_raw) if detail_raw else {}
        else:
            detail = detail_raw or {}
        entries.append(
            AuditEntrySchema(
                id=row["id"],
                timestamp=row["timestamp"],
                actor=row["actor"],
                role=row["role"],
                action=row["action"],
                resource=row["resource"],
                resource_id=row["resource_id"] if row["resource_id"] else None,
                detail=detail,
            )
        )
    return entries