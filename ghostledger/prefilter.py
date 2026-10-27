"""Cheap first pass: which emails are worth a model's time at all.

A real mailbox is 10-20 years of mail. Gemma on a laptop CPU reads one email in ~40 s, so it should
only read emails that could be about money: statements, policies, folios, deposits, bills. This
pass is deliberately generous; missing a statement here means missing an asset, while letting a
newsletter through only costs 40 seconds.
"""
from __future__ import annotations

import re

from .schema import Email

MONEY_WORDS = re.compile(
    r"\b(statement|a/?c|account|deposit|fd|fixed deposit|matur\w*|policy|premium|sum assured|folio|units|nav|"
    r"mutual fund|demat|dp id|holdings?|shares?|dividend|iepf|pension|ppo|ppf|provident|uan|epf|gold bond|sgb|"
    r"credit card|card ending|loan|emi|renew\w*|subscription|auto-?pay|bill|insur\w*|claim|nominee)\b",
    re.I,
)
NUMBER = re.compile(r"\d{4,}")


def worth_reading(e: Email) -> tuple[bool, str]:
    text = f"{e.subject}\n{e.body}"
    words = set(m.group(0).lower() for m in MONEY_WORDS.finditer(text))
    if not words:
        return False, "no money words"
    if not NUMBER.search(text) and "subscription" not in words and not any(w.startswith("renew") for w in words):
        return False, "money words but no account-like number"
    return True, ", ".join(sorted(words)[:4])


def split(emails: list[Email]) -> tuple[list[Email], list[tuple[Email, str]]]:
    keep, skip = [], []
    for e in emails:
        ok, why = worth_reading(e)
        (keep if ok else skip).append(e if ok else (e, why))
    return keep, skip
