import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import feed

from fixes.common.data import catalog_items

T0 = datetime(2026, 11, 12, 6, 43)


def test_publish_writes_one_entry():
    c = feed.connect()
    feed.publish_version(
        c, "investor-match", "1.0.0", "Investor Match", "Find investors", T0
    )
    u = feed.recent_updates(c)["updates"]
    assert (
        len(u) == 1
        and u[0]["title"] == "New: Investor Match"
        and u[0]["kind"] == "pas_update"
    )


def test_second_version_is_an_update_not_new():
    c = feed.connect()
    feed.publish_version(c, "s", "1.0.0", "S", "", T0)
    feed.publish_version(c, "s", "1.0.1", "S", "", T0 + timedelta(hours=1))
    titles = [u["title"] for u in feed.recent_updates(c)["updates"]]
    assert titles == ["S updated to 1.0.1", "New: S"]


def test_failed_publish_leaves_no_version_and_no_entry():
    c = feed.connect()
    with pytest.raises(RuntimeError):
        feed.publish_version(c, "s", "1.0.0", "S", "", T0, fail_after_insert=True)
    assert c.execute("SELECT COUNT(*) FROM solution_versions").fetchone()[0] == 0
    assert feed.recent_updates(c)["updates"] == []


def test_pagination_and_kind_filter():
    c = feed.connect()
    for i in range(5):
        feed.publish_version(
            c, f"s{i}", "1.0.0", f"S{i}", "", T0 + timedelta(minutes=i)
        )
    p1 = feed.recent_updates(c, limit=2)
    p2 = feed.recent_updates(c, limit=2, cursor=int(p1["next_cursor"]))
    assert [u["solutionId"] for u in p1["updates"] + p2["updates"]] == [
        "s4",
        "s3",
        "s2",
        "s1",
    ]
    assert feed.recent_updates(c, kinds=["customer_story"])["updates"] == []


def test_backfill_real_catalog_gives_21_entries_and_is_idempotent():
    c = feed.connect()
    for it in catalog_items():
        c.execute(
            "INSERT INTO solution_versions VALUES (?,?,?,?,?)",
            (
                it["locator"]["solutionId"],
                it["locator"]["version"],
                it["name"],
                it["subtitle"],
                it["publishedAt"],
            ),
        )
    assert feed.backfill(c) == 21
    assert feed.backfill(c) == 0
    assert len(feed.recent_updates(c, limit=100)["updates"]) == 21
