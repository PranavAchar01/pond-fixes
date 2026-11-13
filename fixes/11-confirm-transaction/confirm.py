"""Confirm a workflow in one transaction.

Observed 2026-11-12 (data in README): pond_workflow_confirm returned
status "confirmed" and live_version 3, but actor_name was still
"[Editing] Statsmodels question digest" and actor_note still
"Building the weekday digest"; the "[Deployed]" name only appeared as an
instruction (agent.rename_to) for the client to apply later. A reader in
between sees a confirmed workflow labelled as being edited.

confirm() sets status, live_version, actor_name, actor_note and actor_at in
one UPDATE guarded by expected_revision, so readers see either the old state
or the new one, never a mix, and a stale confirm is rejected.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS workflows (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL, revision INTEGER NOT NULL,
  live_version INTEGER, actor_name TEXT, actor_note TEXT, actor_at TEXT);
"""


class RevisionConflict(Exception):
    pass


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.executescript(SCHEMA)
    return conn


def read(conn, wid: str) -> dict:
    cur = conn.execute("SELECT * FROM workflows WHERE id=?", (wid,))
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, cur.fetchone()))


def confirm(conn, wid: str, expected_revision: int, now: datetime) -> dict:
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            """UPDATE workflows SET status='confirmed', live_version=revision,
                   actor_name='[Deployed] ' || name,
                   actor_note='Live: revision ' || revision,
                   actor_at=?
               WHERE id=? AND revision=?""",
            (now.isoformat(), wid, expected_revision),
        )
        if cur.rowcount != 1:
            raise RevisionConflict(f"{wid} is not at revision {expected_revision}")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return read(conn, wid)


def consistent(state: dict) -> bool:
    """Invariant any reader can check: a confirmed workflow is labelled deployed at its live revision."""
    if state["status"] != "confirmed":
        return True
    return (
        state["live_version"] == state["revision"]
        and state["actor_name"] == f"[Deployed] {state['name']}"
        and state["actor_note"] == f"Live: revision {state['revision']}"
    )
