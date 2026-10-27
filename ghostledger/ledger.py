"""Merge what every email said into one inheritance map: one entry per holding, with its evidence.

Two emails describe the same holding when they agree on kind, institution and the last four digits of
the identifier. The latest grounded status wins, except that "closed" sticks (closures don't reopen)
and a "matured_unclaimed" is only cleared by later evidence that it was paid or closed.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .grounding import NEEDS_NO_ID, inst_tokens
from .routes import route_for
from .schema import Email, Reading

LONG_NUMBER = re.compile(r"\b[A-Z]{0,4}[/-]?\d[\dA-Z/-]{5,}\b")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4}|\d{4}-\d{2}")  # dates and financial years (2017-18)
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


def mask(text: str) -> str:
    """Hide all but the last four characters of account-like numbers in anything we show or publish."""
    def hide(m: re.Match) -> str:
        s = m.group(0)
        digits = sum(ch.isdigit() for ch in s)
        if digits < 6 or "," in s or DATE.fullmatch(s):
            return s
        return "X" * (len(s) - 4) + s[-4:]
    return LONG_NUMBER.sub(hide, PAN.sub("XXXXX####X", text))


@dataclass
class Holding:
    kind: str
    institution: str
    last4: str
    status: str = "unknown"
    first_seen: str = ""
    last_seen: str = ""
    idents: set[str] = field(default_factory=set)  # every identifier form seen (digits only)
    evidence: list[dict] = field(default_factory=list)  # {email, date, quote, status}
    after_death: list[str] = field(default_factory=list)  # dates of charges/notices after the date of death

    @property
    def inst_key(self) -> str:
        toks = inst_tokens(self.institution)
        return toks[0] if toks else self.institution.lower()

    @property
    def route(self) -> dict:
        return route_for(self.kind, self.status)

    def same_as(self, kind: str, institution: str, last4: str, ident_digits: str, evidence: str = "") -> bool:
        if kind != self.kind:
            return False
        # the same long number (a DP ID, a folio) is the same holding, whoever the email is from
        runs = set(re.findall(r"\d{6,}", ident_digits))
        if runs and any(r in d for r in runs for d in self.idents):
            return True
        toks = inst_tokens(institution)
        if (toks[0] if toks else institution.lower()) != self.inst_key:
            return False
        if not last4 or not self.last4:
            return kind in NEEDS_NO_ID
        if last4 == self.last4 or any(last4 in d for d in self.idents) or self.last4 in ident_digits:
            return True
        # one email quotes the account, another the PPO: the earlier evidence already names this number
        ev_digits = re.sub(r"\D", "", " ".join(e["quote"] for e in self.evidence))
        return last4 in ev_digits or self.last4 in re.sub(r"\D", "", evidence)

    @classmethod
    def from_dict(cls, d: dict) -> "Holding":
        last4 = (d.get("identifier") or "").replace("X", "")
        h = cls(d["kind"], d["institution"], last4, d.get("status", "unknown"), d.get("first_seen", ""),
                d.get("last_seen", ""), set(), list(d.get("evidence", [])), list(d.get("after_death", [])))
        return h

    def to_dict(self) -> dict:
        return {"kind": self.kind, "institution": self.institution,
                "identifier": f"XXXX{self.last4}" if self.last4 else "",
                "status": self.status, "first_seen": self.first_seen, "last_seen": self.last_seen,
                "emails": len(self.evidence), "action": self.route["action"], "after_death": self.after_death,
                "evidence": [{**ev, "quote": mask(ev["quote"])} for ev in self.evidence]}


ACTION_ORDER = {"CLAIM (URGENT)": 0, "CLAIM": 1, "STOP + FAMILY PENSION": 2, "INFORM + CLOSE": 3, "INFORM": 4,
                "CANCEL": 5, "TRANSFER": 6, "CHECK": 7, "NOTHING (closed)": 8}


def _update_status(h: Holding, new: str) -> None:
    if h.status == "closed":
        return  # closures don't reopen
    if h.status in ("matured_unclaimed", "at_risk") and new != "closed":
        return  # a routine later email doesn't clear an unclaimed/at-risk warning
    if new != "unknown" or h.status == "unknown":
        h.status = new


def build(emails: list[Email], readings: list[Reading], date_of_death: str = "") -> tuple[list[Holding], list[dict]]:
    """Returns (holdings ranked by what to do first, ignored scam emails)."""
    by_id = {e.id: e for e in emails}
    holdings: list[Holding] = []
    names: dict[int, Counter] = {}
    last4s: dict[int, Counter] = {}
    ignored: list[dict] = []
    for r in sorted(readings, key=lambda r: by_id[r.email_id].date or ""):
        e = by_id[r.email_id]
        day = (e.date or "")[:10]
        if r.is_scam:
            if r.items or r.scam_reasons or r.model_says_scam:
                ignored.append({"email": e.id, "date": day, "subject": e.subject, "sender": e.sender,
                                "why": r.scam_reasons or ["the model flagged it as a scam"]})
            continue
        for it in r.items:
            if not it.ok:
                continue
            digits = " ".join(re.findall(r"\d+", it.identifier or ""))
            h = next((h for h in holdings if h.same_as(it.kind, it.institution, it.last4, digits, it.evidence)), None)
            if h is None:
                h = Holding(it.kind, it.institution, it.last4, first_seen=day)
                holdings.append(h)
                names[id(h)] = Counter()
                last4s[id(h)] = Counter()
            if it.last4:
                last4s[id(h)][it.last4] += 1
            if digits:
                h.idents.add(digits)
            names[id(h)][it.institution] += 1
            h.last_seen = day
            h.evidence.append({"email": e.id, "date": day, "quote": it.evidence, "status": it.status})
            if date_of_death and day > date_of_death and day not in h.after_death:
                h.after_death.append(day)
            _update_status(h, it.status)
    for h in holdings:
        h.institution = names[id(h)].most_common(1)[0][0]
        if last4s[id(h)]:
            h.last4 = last4s[id(h)].most_common(1)[0][0]  # the number most emails use
    ranked = sorted(holdings, key=lambda h: (ACTION_ORDER.get(h.route["action"], 9),
                                             h.status not in ("matured_unclaimed", "at_risk"), h.kind, h.institution))
    return ranked, ignored
