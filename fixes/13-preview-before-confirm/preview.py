"""Preview before confirm.

Today a workflow can be confirmed, and shown as running, before any of its sources has returned
data. The first proof that it works is the first real run. In my build that came 16.5 minutes
after confirm, and it failed with 0 results and an empty digest.

`preview()` runs every source step once on a small sample while the workflow is still a draft:
one query per source, a short window, a hard time budget, and the workflow's own scope check on
whatever comes back. Each step gets a verdict, and the canvas can show it on the node. `confirm()`
refuses a workflow whose preview found nothing in scope, unless the member confirms anyway, and
then the reason is stored on the workflow.

Fetching is injected, so the replay test feeds it the searches captured during the build.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Source:
    step_id: str
    query: str


@dataclass
class Item:
    title: str
    url: str
    source: str


@dataclass
class Fetched:
    items: list[Item]
    seconds: float
    timed_out: bool = False


@dataclass
class StepVerdict:
    step_id: str
    status: str  # "ok" | "empty" | "out_of_scope" | "timeout"
    found: int
    in_scope: int
    seconds: float
    sample: list[Item] = field(default_factory=list)
    why: list[str] = field(default_factory=list)


@dataclass
class Preview:
    steps: list[StepVerdict]
    seconds: float
    seconds_parallel: float

    @property
    def ready(self) -> bool:
        return any(s.in_scope > 0 for s in self.steps)

    @property
    def summary(self) -> str:
        found = sum(s.found for s in self.steps)
        kept = sum(s.in_scope for s in self.steps)
        return f"{kept} in scope of {found} found across {len(self.steps)} sources"


def preview(
    sources: list[Source],
    fetch: Callable[[Source], Fetched],
    in_scope: Callable[[Item], tuple[bool, str]],
    sample_size: int = 3,
) -> Preview:
    verdicts = []
    for src in sources:
        got = fetch(src)
        kept, why = [], []
        for item in got.items:
            ok, reason = in_scope(item)
            if ok:
                kept.append(item)
            elif reason and reason not in why:
                why.append(reason)
        if got.timed_out:
            status = "timeout"
        elif not got.items:
            status = "empty"
        elif not kept:
            status = "out_of_scope"
        else:
            status = "ok"
        verdicts.append(
            StepVerdict(
                src.step_id,
                status,
                len(got.items),
                len(kept),
                got.seconds,
                (kept or got.items)[:sample_size],
                why,
            )
        )
    total = sum(v.seconds for v in verdicts)
    return Preview(
        verdicts,
        round(total, 2),
        round(max((v.seconds for v in verdicts), default=0.0), 2),
    )


class NeedsPreview(Exception):
    pass


def confirm(
    workflow: dict, pv: Preview | None, force_reason: str | None = None
) -> dict:
    """Confirm a draft. Without a passing preview, only an explicit reason lets it through."""
    if pv is None:
        raise NeedsPreview(
            "Run a preview first: confirm needs evidence that at least one source returns data."
        )
    if not pv.ready and not force_reason:
        raise NeedsPreview(
            f"Preview found nothing to deliver ({pv.summary}). Fix the sources, or confirm with a reason."
        )
    out = dict(workflow, status="confirmed", preview_summary=pv.summary)
    if not pv.ready:
        out["confirmed_without_results"] = force_reason
    return out
