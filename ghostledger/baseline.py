"""The no-model baseline: keywords + regex, the way you'd write it in an afternoon.

It gets the same prefilter and scam checks as Gemma, and the same grounding pass, so the eval
compares only the reading step.
"""
from __future__ import annotations

import re

from . import grounding
from .schema import Email, Item, Reading

IDENT = re.compile(r"(?:a/c|account(?: no\.?)?|card ending|account ending|policy(?: no\.?)?|folio(?: no\.?)?|receipt no\.?|"
                   r"uan|ppo no\.?|holding id|client id|subscriber id|rr no\.?|mobile number)\s*:?\s*((?-i:[A-Z0-9/-]*\d{3,}[A-Z0-9/-]*))", re.I)
KIND_RULES = [
    (r"fixed deposit|fd receipt|\bfd\b", "fixed_deposit"), (r"\bppf\b", "ppf"), (r"gold bond|\bsgb\b", "gold_bond"),
    (r"pension|ppo", "pension"), (r"folio|mutual fund|units", "mutual_fund"), (r"demat|dp id", "demat"),
    (r"physical shareholding|shareholder", "shares_physical"), (r"health|mediclaim", "health_insurance"),
    (r"policy|premium|sum assured", "life_insurance"), (r"\buan\b|epf|provident", "provident_fund"),
    (r"credit card", "credit_card"), (r"subscription|renew|plan", "subscription"), (r"bill for|electricity", "utility"),
    (r"postpaid|mobile", "subscription"), (r"savings|a/c|account", "bank_account"),
]


def _kind(text: str) -> str:
    for pat, kind in KIND_RULES:
        if re.search(pat, text, re.I):
            return kind
    return "other"


def _status(text: str) -> str:
    t = text.lower()
    if re.search(r"\b(has been|was) closed\b", t):
        return "closed"
    if "matur" in t and re.search(r"unclaimed|unpaid", t):
        return "matured_unclaimed"
    if "iepf" in t or "investor education" in t:
        return "at_risk"
    if "no contribution" in t or "inoperative" in t:
        return "inoperative"
    return "active"


def read(e: Email) -> Reading:
    institution = e.sender.split("<")[0].strip().strip('"')
    text = e.body
    items, seen = [], set()
    for m in IDENT.finditer(text):
        ident = m.group(1).strip(" -/")
        line = next((ln for ln in text.splitlines() if m.group(0)[:20] in ln), m.group(0))
        it = Item(kind=_kind(e.subject + " " + line), institution=institution, identifier=ident,
                  status=_status(text), evidence=line.strip())
        if it.last4 in seen:
            continue
        seen.add(it.last4)
        items.append(it)
    for it in items:
        why = grounding.check(it, e)
        it.ok, it.reason = why is None, why or ""
    return Reading(email_id=e.id, about_holding=bool(items), items=items[:4], meta={"baseline": True})
