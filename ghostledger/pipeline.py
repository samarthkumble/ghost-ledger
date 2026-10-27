"""One pass over a mailbox: cheap filter -> scam checks -> Gemma reads what's left.

The same functions run from the CLI and inside the Temporal workflow (one activity per email), so a
crash or a closed laptop lid only costs the email that was in flight.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from . import prefilter, scam
from .schema import Email, Reading

Reader = Callable[[Email], Reading]


@dataclass
class Scan:
    emails: list[Email]
    readings: list[Reading] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (email id, why it wasn't read)

    @property
    def read_count(self) -> int:
        return sum(1 for r in self.readings if not r.meta.get("not_read"))


def triage(e: Email) -> tuple[str, str]:
    """('read', '') if Gemma should read it, ('scam', reasons) or ('skip', why) otherwise."""
    reasons = scam.check(e)
    if reasons:
        return "scam", "; ".join(reasons)
    keep, why = prefilter.worth_reading(e)
    if not keep:
        return "skip", why
    return "read", ""


def scam_reading(e: Email) -> Reading:
    return Reading(email_id=e.id, scam_reasons=scam.check(e), meta={"not_read": True})


def run(emails: Iterable[Email], reader: Reader, on_progress: Callable[[int, int, Email], None] | None = None) -> Scan:
    emails = list(emails)
    out = Scan(emails)
    todo = []
    for e in emails:
        verdict, why = triage(e)
        if verdict == "skip":
            out.skipped.append((e.id, why))
        elif verdict == "scam":
            out.readings.append(scam_reading(e))  # never sent to the model, never becomes an asset
        else:
            todo.append(e)
    for i, e in enumerate(todo, 1):
        if on_progress:
            on_progress(i, len(todo), e)
        out.readings.append(reader(e))
    return out
