"""Multi-source watches that stay alive while the workflow using them is live.

Today (tools/list, 2026-11-12): a Reddit watch searches "optionally inside one
subreddit"; repeat daily runs "for 7 days after the first run"; a plan has a
limit on active watches (3 on the plan Pranav used); pond_watch_extend adds 7
days and must be called by hand. A digest over 4 subreddits plus Hacker News
needs 5 watches, more than the cap, and dies after a week.

Here a watch holds a list of sources (scraper + query + optional subreddit),
the active-watch limit counts watches, and a watch linked to a live workflow
is renewed on each tick while that workflow is live. When the workflow is
paused or archived the watch runs out its current window and expires.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class Source:
    scraper: str  # "reddit" | "hackernews" | ...
    query: str
    subreddit: str | None = None


@dataclass
class Watch:
    watch_id: str
    owner: str
    sources: list[Source]
    expires_at: datetime
    workflow_id: str | None = None
    status: str = "active"


class LimitError(Exception):
    pass


@dataclass
class WatchService:
    clock: Callable[[], datetime]
    active_limit: int = 3
    max_sources: int = 10
    is_workflow_live: Callable[[str], bool] = lambda wid: False
    watches: dict[str, Watch] = field(default_factory=dict)

    def active(self, owner: str) -> list[Watch]:
        self.tick()
        return [
            w
            for w in self.watches.values()
            if w.owner == owner and w.status == "active"
        ]

    def start(
        self,
        watch_id: str,
        owner: str,
        sources: list[Source],
        workflow_id: str | None = None,
    ) -> Watch:
        if not sources or len(sources) > self.max_sources:
            raise ValueError(
                f"a watch takes 1 to {self.max_sources} sources; got {len(sources)}"
            )
        if len(self.active(owner)) >= self.active_limit:
            raise LimitError(f"{owner} already has {self.active_limit} active watches")
        w = Watch(
            watch_id,
            owner,
            list(dict.fromkeys(sources)),
            self.clock() + WINDOW,
            workflow_id,
        )
        self.watches[watch_id] = w
        return w

    def tick(self) -> None:
        """Renew watches whose workflow is live; expire the rest at their window end."""
        now = self.clock()
        for w in self.watches.values():
            if w.status != "active":
                continue
            if w.workflow_id and self.is_workflow_live(w.workflow_id):
                w.expires_at = max(w.expires_at, now + WINDOW)
            elif now >= w.expires_at:
                w.status = "expired"

    def due_runs(self) -> list[tuple[str, Source]]:
        """One daily run fans out to every source of every active watch."""
        self.tick()
        return [
            (w.watch_id, s)
            for w in self.watches.values()
            if w.status == "active"
            for s in w.sources
        ]


def watches_needed_today(sources: list[Source]) -> int:
    """Under the current model: one watch per Reddit subreddit, one per other query."""
    return len({(s.scraper, s.query, s.subreddit) for s in sources})
