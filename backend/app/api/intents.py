"""Intent CRUD and compilation endpoints.

All data endpoints enforce role-based authorization:
* viewer    — list / get / compiled detail
* operator  — create / compile / delete
* admin    — audit log (handled in api.audit)

Each intent record and its compiled result are stored in SQLite with
UTC timestamps.  Mutations write to the audit log atomically.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import User, require_role
from app.core.audit import log_action
from app.core.database import fetch_all, fetch_one, get_db
from app.models.domain import IntentDefinition
from app.models.schemas import (
    CompiledIntentSchema,
    IntentCreateSchema,
    IntentSchema,
    PaginatedIntents,
)
from app.services.intent_engine import IntentEngine

router = APIRouter(tags=["intents"])

_engine: IntentEngine | None = None


def get_engine() -> IntentEngine:
    global _engine
    if _engine is None:
        _engine = IntentEngine()
    return _engine


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_intent(row) -> IntentSchema:
    return IntentSchema(
        id=row["id"],
        style_archetype=row["style_archetype"],
        subject=row["subject"],
        mood=row["mood"],
        lighting=row["lighting"],
        composition=row["composition"],
        resolution_w=row["resolution_w"],
        resolution_h=row["resolution_h"],
        quality=row["quality"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_compiled(row) -> CompiledIntentSchema:
    layers_data = json.loads(row["positive_layers"])
    return CompiledIntentSchema(
        id=row["id"],
        intent_id=row["intent_id"],
        positive_prompt=row["positive_prompt"],
        negative_prompt=row["negative_prompt"],
        cfg_scale=row["cfg_scale"],
        steps=row["steps"],
        scheduler=row["scheduler"],
        seed=row["seed"],
        width=row["width"],
        height=row["height"],
        denoising_start=row["denoising_start"],
        denoising_end=row["denoising_end"],
        positive_layers=layers_data,
        model_recommendation=row["model_rec"],
        created_at=row["created_at"],
    )


# ---------------------------------------------------------------------------
# List (viewer+)
# ---------------------------------------------------------------------------

@router.get("/", response_model=PaginatedIntents)
def list_intents(
    page: int = Query(default=1, ge=1, le=10000),
    per_page: int = Query(default=20, ge=1, le=200),
    style_archetype: str | None = Query(default=None),
    _user: User = Depends(require_role("viewer")),
):
    offset = (page - 1) * per_page

    filters: list[str] = []
    filter_params: list[Any] = []

    if style_archetype is not None:
        filters.append("style_archetype = ?")
        filter_params.append(style_archetype)

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    query_count = f"SELECT COUNT(*) as c FROM intents {where_clause}"
    query_list = (
        f"SELECT * FROM intents {where_clause} "
        f"ORDER BY created_at DESC LIMIT ? OFFSET ?"
    )
    all_params = tuple(filter_params + [per_page, offset])

    with get_db() as conn:
        total = fetch_one(conn, query_count, tuple(filter_params))["c"]
        rows = fetch_all(conn, query_list, all_params)

        intent_ids = [r["id"] for r in rows]
        compiled_map: dict[str, CompiledIntentSchema] = {}
        if intent_ids:
            placeholders = ", ".join("?" * len(intent_ids))
            compiled_rows = fetch_all(
                conn,
                f"SELECT * FROM compiled_intents "
                f"WHERE intent_id IN ({placeholders}) "
                f"ORDER BY created_at DESC",
                tuple(intent_ids),
            )
            for row in compiled_rows:
                compiled_map[row["intent_id"]] = _row_to_compiled(row)

    intents = [_row_to_intent(r) for r in rows]
    return PaginatedIntents(
        intents=intents,
        compiled=compiled_map,
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + per_page < total,
    )


# ---------------------------------------------------------------------------
# Create (operator+)
# ---------------------------------------------------------------------------

@router.post("/", response_model=IntentSchema, status_code=status.HTTP_201_CREATED)
def create_intent(
    payload: IntentCreateSchema,
    user: User = Depends(require_role("operator")),
):
    intent_id = f"int_{uuid.uuid4().hex[:12]}"
    now = _utc_now()

    definition = IntentDefinition(
        style_archetype=payload.style_archetype,
        subject=payload.subject,
        mood=payload.mood,
        lighting=payload.lighting,
        composition=payload.composition,
        resolution_w=payload.resolution_w,
        resolution_h=payload.resolution_h,
        quality=payload.quality,
    )

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO intents (id, style_archetype, subject, mood, lighting,
                                  composition, resolution_w, resolution_h, quality,
                                  created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intent_id,
                definition.style_archetype,
                definition.subject,
                definition.mood,
                definition.lighting,
                definition.composition,
                definition.resolution_w,
                definition.resolution_h,
                definition.quality,
                now,
                now,
            ),
        )

    log_action(
        actor=user.subject,
        role=user.role,
        action="intent.create",
        resource="intents",
        resource_id=intent_id,
        detail={"archetype": definition.style_archetype, "subject": definition.subject},
    )

    row = {
        "id": intent_id,
        "style_archetype": definition.style_archetype,
        "subject": definition.subject,
        "mood": definition.mood,
        "lighting": definition.lighting,
        "composition": definition.composition,
        "resolution_w": definition.resolution_w,
        "resolution_h": definition.resolution_h,
        "quality": definition.quality,
        "created_at": now,
        "updated_at": now,
    }
    return _row_to_intent(row)


# ---------------------------------------------------------------------------
# Get single (viewer+)
# ---------------------------------------------------------------------------

@router.get("/{intent_id}", response_model=IntentSchema)
def get_intent(
    intent_id: str,
    _user: User = Depends(require_role("viewer")),
):
    with get_db() as conn:
        row = fetch_one(conn, "SELECT * FROM intents WHERE id = ?", (intent_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Intent not found")
    return _row_to_intent(row)


# ---------------------------------------------------------------------------
# Compile (operator+)
# ---------------------------------------------------------------------------

@router.post("/{intent_id}/compile", response_model=CompiledIntentSchema)
def compile_intent(
    intent_id: str,
    user: User = Depends(require_role("operator")),
):
    with get_db() as conn:
        intent_row = fetch_one(conn, "SELECT * FROM intents WHERE id = ?", (intent_id,))
        if intent_row is None:
            raise HTTPException(status_code=404, detail="Intent not found")

        existing = fetch_one(
            conn,
            "SELECT * FROM compiled_intents WHERE intent_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (intent_id,),
        )
        if existing:
            compiled = _row_to_compiled(existing)
        else:
            engine = get_engine()
            definition = IntentDefinition(
                style_archetype=intent_row["style_archetype"],
                subject=intent_row["subject"],
                mood=intent_row["mood"],
                lighting=intent_row["lighting"],
                composition=intent_row["composition"],
                resolution_w=intent_row["resolution_w"],
                resolution_h=intent_row["resolution_h"],
                quality=intent_row["quality"],
            )
            result = engine.compile(definition)

            now = _utc_now()
            conn.execute(
                """
                INSERT INTO compiled_intents (
                    id, intent_id, positive_prompt, negative_prompt,
                    cfg_scale, steps, scheduler, seed, width, height,
                    denoising_start, denoising_end, positive_layers,
                    model_rec, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    intent_id,
                    result.positive_prompt,
                    result.negative_prompt,
                    result.cfg_scale,
                    result.steps,
                    result.scheduler,
                    result.seed,
                    result.width,
                    result.height,
                    result.denoising_start,
                    result.denoising_end,
                    json.dumps([asdict(l) for l in result.positive_layers]),
                    result.model_recommendation,
                    now,
                ),
            )
            compiled = CompiledIntentSchema(
                id=result.id,
                intent_id=intent_id,
                positive_prompt=result.positive_prompt,
                negative_prompt=result.negative_prompt,
                cfg_scale=result.cfg_scale,
                steps=result.steps,
                scheduler=result.scheduler,
                seed=result.seed,
                width=result.width,
                height=result.height,
                denoising_start=result.denoising_start,
                denoising_end=result.denoising_end,
                positive_layers=[asdict(l) for l in result.positive_layers],
                model_recommendation=result.model_recommendation,
                created_at=now,
            )

    log_action(
        actor=user.subject,
        role=user.role,
        action="intent.compile",
        resource="compiled_intents",
        resource_id=compiled.id,
        detail={"intent_id": intent_id, "cfg_scale": compiled.cfg_scale, "steps": compiled.steps},
    )
    return compiled


# ---------------------------------------------------------------------------
# Delete (operator+)
# ---------------------------------------------------------------------------

@router.delete("/{intent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_intent(
    intent_id: str,
    user: User = Depends(require_role("operator")),
):
    with get_db() as conn:
        result = conn.execute("DELETE FROM intents WHERE id = ?", (intent_id,))
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Intent not found")

    log_action(
        actor=user.subject,
        role=user.role,
        action="intent.delete",
        resource="intents",
        resource_id=intent_id,
    )
    return None


# ---------------------------------------------------------------------------
# Get compiled by ID (viewer+)
# ---------------------------------------------------------------------------

@router.get("/compiled/{compiled_id}", response_model=CompiledIntentSchema)
def get_compiled(
    compiled_id: str,
    _user: User = Depends(require_role("viewer")),
):
    with get_db() as conn:
        row = fetch_one(
            conn, "SELECT * FROM compiled_intents WHERE id = ?", (compiled_id,)
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Compiled intent not found")
    return _row_to_compiled(row)