"""SQLite persistence layer with WAL mode, parameterized queries, and
transactional mutations.

Uses Python's built-in sqlite3 for zero external dependencies.  Connection
lifecycle is managed by a context manager that guarantees commit-on-success
and rollback-on-error semantics.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.core.config import get_settings


def _resolve_db_path(database_url: str) -> str:
    """Translate a SQLAlchemy-style SQLite URL into a filesystem path."""
    if database_url.startswith("sqlite:///"):
        path = database_url[len("sqlite:///"):]
        if path == ":memory:":
            return ":memory:"
        return path
    if database_url.startswith("sqlite://"):
        return ":memory:"
    return database_url


def _connect(database_url: str) -> sqlite3.Connection:
    db_path = _resolve_db_path(database_url)
    if db_path == ":memory:":
        conn = sqlite3.connect(":memory:", check_same_thread=False)
    else:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS intents (
    id              TEXT PRIMARY KEY,
    style_archetype TEXT NOT NULL,
    subject         TEXT NOT NULL,
    mood            TEXT NOT NULL,
    lighting        TEXT NOT NULL,
    composition     TEXT NOT NULL,
    resolution_w    INTEGER,
    resolution_h    INTEGER,
    quality         TEXT NOT NULL DEFAULT 'standard',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compiled_intents (
    id              TEXT PRIMARY KEY,
    intent_id       TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
    positive_prompt TEXT NOT NULL,
    negative_prompt TEXT NOT NULL,
    cfg_scale       REAL NOT NULL,
    steps           INTEGER NOT NULL,
    scheduler       TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    width           INTEGER NOT NULL,
    height          INTEGER NOT NULL,
    denoising_start REAL NOT NULL,
    denoising_end   REAL NOT NULL,
    positive_layers TEXT NOT NULL,
    model_rec       TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    actor       TEXT NOT NULL,
    role        TEXT NOT NULL,
    action      TEXT NOT NULL,
    resource    TEXT NOT NULL,
    resource_id TEXT,
    detail      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_intents_created   ON intents(created_at);
CREATE INDEX IF NOT EXISTS idx_compiled_intent_id ON compiled_intents(intent_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp   ON audit_log(timestamp);
"""


def init_db(database_url: str | None = None) -> sqlite3.Connection:
    """Create the schema on a connection (used at startup and in tests)."""
    settings = get_settings()
    url = database_url or settings.database_url
    conn = _connect(url)
    conn.executescript(SCHEMA_SQL)
    return conn


@contextmanager
def get_db(database_url: str | None = None) -> Iterator[sqlite3.Connection]:
    """Context-managed database connection with transaction semantics.

    Commits on normal exit, rolls back on exception, and always closes.
    """
    settings = get_settings()
    url = database_url or settings.database_url
    conn = _connect(url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    cur = conn.execute(query, params)
    return cur.fetchall()


def fetch_one(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    cur = conn.execute(query, params)
    return cur.fetchone()