"""Write an updates-feed entry in the same transaction as every publish.

pond_recent_updates returned {"updates": [], "next_cursor": null} on
2026-11-12 while the catalog listed 21 published solutions. The fix ties
the feed to publishing: publish_version() inserts the version row and its
pas_update entry together, so a published version always has an entry and a
rolled-back publish never leaves one. backfill() creates entries for versions
published before the hook existed.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS solution_versions (
  solution_id TEXT NOT NULL, version TEXT NOT NULL, name TEXT NOT NULL,
  subtitle TEXT, published_at TEXT NOT NULL, PRIMARY KEY (solution_id, version));
CREATE TABLE IF NOT EXISTS updates (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, title TEXT NOT NULL,
  body TEXT, subject_ref TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, payload TEXT NOT NULL);
"""
KINDS = {"pas_update", "dataset_update", "customer_story", "official_announcement"}


def connect(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.executescript(SCHEMA)
    return conn


def _entry(conn, solution_id, version, name, subtitle, published_at) -> None:
    first = (
        conn.execute(
            "SELECT COUNT(*) FROM solution_versions WHERE solution_id=?", (solution_id,)
        ).fetchone()[0]
        == 1
    )
    title = f"New: {name}" if first else f"{name} updated to {version}"
    conn.execute(
        "INSERT OR IGNORE INTO updates(kind,title,body,subject_ref,created_at,payload) VALUES (?,?,?,?,?,?)",
        (
            "pas_update",
            title,
            subtitle,
            f"pas:{solution_id}@{version}",
            published_at,
            json.dumps(
                {"solutionId": solution_id, "version": version, "new_solution": first}
            ),
        ),
    )


def publish_version(
    conn,
    solution_id: str,
    version: str,
    name: str,
    subtitle: str,
    published_at: datetime,
    fail_after_insert: bool = False,
) -> None:
    """Publish and record the update atomically. fail_after_insert simulates a crash (tests)."""
    ts = published_at.isoformat()
    conn.execute("BEGIN")
    try:
        conn.execute(
            "INSERT INTO solution_versions VALUES (?,?,?,?,?)",
            (solution_id, version, name, subtitle, ts),
        )
        if fail_after_insert:
            raise RuntimeError("simulated failure")
        _entry(conn, solution_id, version, name, subtitle, ts)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def backfill(conn) -> int:
    """Entries for versions published before the hook. Idempotent."""
    before = conn.execute("SELECT COUNT(*) FROM updates").fetchone()[0]
    rows = conn.execute(
        "SELECT solution_id, version, name, subtitle, published_at FROM solution_versions "
        "ORDER BY published_at"
    ).fetchall()
    conn.execute("BEGIN")
    for sid, ver, name, sub, ts in rows:
        _entry(conn, sid, ver, name, sub, ts)
    conn.execute("COMMIT")
    return conn.execute("SELECT COUNT(*) FROM updates").fetchone()[0] - before


def recent_updates(
    conn, limit: int = 20, kinds: list[str] | None = None, cursor: int | None = None
) -> dict:
    """Same response shape as pond_recent_updates: newest first, cursor = last id seen."""
    q, args = (
        "SELECT id, kind, title, body, created_at, payload FROM updates WHERE 1=1",
        [],
    )
    if kinds:
        q += f" AND kind IN ({','.join('?' * len(kinds))})"
        args += kinds
    if cursor is not None:
        q += " AND id < ?"
        args.append(cursor)
    rows = conn.execute(q + " ORDER BY id DESC LIMIT ?", (*args, limit + 1)).fetchall()
    page = rows[:limit]
    return {
        "updates": [
            {"kind": k, "title": t, "summary": b, "created_at": c, **json.loads(p)}
            for _, k, t, b, c, p in page
        ],
        "next_cursor": str(page[-1][0]) if len(rows) > limit else None,
    }
