import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import confirm as cf

NOW = datetime(2026, 11, 12, 22, 50, 50)
OBSERVED = {
    "id": "pw_1058be43f6482ca64fa86b7d",
    "name": "Statsmodels question digest",
    "status": "confirmed",
    "revision": 3,
    "live_version": 3,
    "actor_name": "[Editing] Statsmodels question digest",
    "actor_note": "Building the weekday digest",
    "actor_at": "2026-11-12T22:50:32.163641Z",
}


def seed(conn, **over):
    row = {**OBSERVED, "status": "draft", "live_version": None, **over}
    conn.execute(
        "INSERT INTO workflows VALUES (:id,:name,:status,:revision,:live_version,:actor_name,"
        ":actor_note,:actor_at)",
        row,
    )


def test_observed_confirm_response_breaks_the_invariant():
    assert not cf.consistent(OBSERVED)


def test_confirm_updates_everything_together():
    c = cf.connect()
    seed(c)
    s = cf.confirm(c, OBSERVED["id"], 3, NOW)
    assert cf.consistent(s)
    assert (
        s["actor_name"] == "[Deployed] Statsmodels question digest"
        and s["live_version"] == 3
    )


def test_stale_revision_is_rejected_and_nothing_changes():
    c = cf.connect()
    seed(c, revision=4)
    with pytest.raises(cf.RevisionConflict):
        cf.confirm(c, OBSERVED["id"], 3, NOW)
    s = cf.read(c, OBSERVED["id"])
    assert s["status"] == "draft" and s["actor_name"].startswith("[Editing]")


def test_concurrent_reader_never_sees_a_mix(tmp_path):
    db = str(tmp_path / "w.db")
    writer, reader = cf.connect(db), cf.connect(db)
    seed(writer)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute(
        "UPDATE workflows SET status='confirmed' WHERE id=?", (OBSERVED["id"],)
    )
    assert (
        cf.read(reader, OBSERVED["id"])["status"] == "draft"
    )  # uncommitted half-update is invisible
    writer.execute("ROLLBACK")
    cf.confirm(writer, OBSERVED["id"], 3, NOW)
    assert cf.consistent(cf.read(reader, OBSERVED["id"]))
