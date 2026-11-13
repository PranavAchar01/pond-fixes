"""Run watchdog for scrape runs.

Every run has a budget. The watchdog, called on each tick (cron, queue
heartbeat, or every status read), does three things:
  1. fails a run that is past its budget with reason "timeout" and the last
     progress it saw, instead of leaving it "running";
  2. fails a run whose progress has not moved for `stall_after` with reason
     "stalled";
  3. lets stopping a watch cancel its in-flight run, with reason "watch_stopped".

Status reads always return progress (items_found, pages_done, last_progress_at)
and, once terminal, failure_reason. The clock is injected so tests use a fake.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

TERMINAL = {"succeeded", "failed", "cancelled"}


@dataclass
class Run:
    run_id: str
    watch_id: str
    started_at: datetime
    budget: timedelta = timedelta(minutes=10)
    status: str = "running"
    items_found: int = 0
    pages_done: int = 0
    last_progress_at: datetime | None = None
    finished_at: datetime | None = None
    failure_reason: str | None = None
    failure_detail: str | None = None

    def view(self, now: datetime) -> dict:
        elapsed = (self.finished_at or now) - self.started_at
        return {
            "run_id": self.run_id,
            "status": self.status,
            "progress": {
                "items_found": self.items_found,
                "pages_done": self.pages_done,
                "last_progress_at": self.last_progress_at.isoformat()
                if self.last_progress_at
                else None,
            },
            "elapsed_s": int(elapsed.total_seconds()),
            "budget_s": int(self.budget.total_seconds()),
            "failure_reason": self.failure_reason,
            "failure_detail": self.failure_detail,
        }


@dataclass
class Watchdog:
    clock: Callable[[], datetime]
    stall_after: timedelta = timedelta(minutes=5)
    cancel_worker: Callable[[str], None] = lambda run_id: None
    runs: dict[str, Run] = field(default_factory=dict)

    def start(
        self, run_id: str, watch_id: str, budget: timedelta = timedelta(minutes=10)
    ) -> Run:
        r = Run(run_id, watch_id, self.clock(), budget)
        r.last_progress_at = r.started_at
        self.runs[run_id] = r
        return r

    def progress(self, run_id: str, items_found: int, pages_done: int) -> None:
        r = self.runs[run_id]
        if r.status in TERMINAL:
            return
        if items_found != r.items_found or pages_done != r.pages_done:
            r.items_found, r.pages_done, r.last_progress_at = (
                items_found,
                pages_done,
                self.clock(),
            )

    def succeed(self, run_id: str) -> None:
        r = self.runs[run_id]
        if r.status not in TERMINAL:
            r.status, r.finished_at = "succeeded", self.clock()

    def _end(
        self, r: Run, status: str, reason: str, detail: str, at: datetime | None = None
    ) -> None:
        """End a run. `at` is the deadline it crossed, so a late tick still records the true end time."""
        end = min(at, self.clock()) if at else self.clock()
        r.status, r.finished_at, r.failure_reason, r.failure_detail = (
            status,
            end,
            reason,
            detail,
        )
        self.cancel_worker(r.run_id)

    def tick(self) -> list[str]:
        """Enforce budgets and stall limits. Returns the run_ids it ended."""
        now, ended = self.clock(), []
        for r in self.runs.values():
            if r.status in TERMINAL:
                continue
            if now - r.started_at >= r.budget:
                self._end(
                    r,
                    "failed",
                    "timeout",
                    f"no result within the {int(r.budget.total_seconds() // 60)} min budget; "
                    f"{r.items_found} items and {r.pages_done} pages done",
                    at=r.started_at + r.budget,
                )
                ended.append(r.run_id)
            elif now - (r.last_progress_at or r.started_at) >= self.stall_after:
                self._end(
                    r,
                    "failed",
                    "stalled",
                    f"no progress for {int(self.stall_after.total_seconds() // 60)} min; "
                    f"{r.items_found} items and {r.pages_done} pages done",
                    at=(r.last_progress_at or r.started_at) + self.stall_after,
                )
                ended.append(r.run_id)
        return ended

    def stop_watch(self, watch_id: str) -> list[str]:
        ended = []
        for r in self.runs.values():
            if r.watch_id == watch_id and r.status not in TERMINAL:
                self._end(
                    r,
                    "cancelled",
                    "watch_stopped",
                    "the watch was stopped while this run was in flight",
                )
                ended.append(r.run_id)
        return ended

    def status(self, run_id: str) -> dict:
        self.tick()  # a status read can never show a run past its budget as running
        return self.runs[run_id].view(self.clock())


def minutes_saved(observed: timedelta, budget: timedelta) -> float:
    """Wall-clock minutes a caller stops waiting earlier when the run fails at its budget."""
    return max(0.0, (observed - budget).total_seconds() / 60)
