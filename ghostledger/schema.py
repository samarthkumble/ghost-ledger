"""Data shapes shared by every part of Ghost Ledger."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# What a record in someone's financial life can be. The family's next step depends on the kind.
KINDS = [
    "bank_account", "fixed_deposit", "ppf", "gold_bond", "pension",
    "mutual_fund", "demat", "shares_physical",
    "life_insurance", "health_insurance", "provident_fund",
    "credit_card", "loan", "subscription", "utility", "other",
]
STATUSES = ["active", "closed", "matured_unclaimed", "inoperative", "at_risk", "unknown"]


@dataclass
class Email:
    id: str
    subject: str
    sender: str  # "Name <addr@domain>"
    date: Optional[str]  # ISO 8601
    body: str

    @property
    def sender_domain(self) -> str:
        addr = self.sender.rsplit("<", 1)[-1].rstrip(">").strip().lower()
        return addr.split("@", 1)[1] if "@" in addr else ""

    @property
    def full_text(self) -> str:
        return f"From: {self.sender}\nSubject: {self.subject}\n\n{self.body}"


@dataclass
class Item:
    """One thing an email says the owner holds, owes or pays for, with the sentence that says so."""
    kind: str
    institution: str
    identifier: Optional[str]
    status: str
    evidence: str
    ok: bool = True
    reason: str = ""  # why grounding rejected it

    @property
    def last4(self) -> str:
        """Last four digits of the longest digit run: "10293341 / 72" -> 3341, "KA/EDU/58/11604" -> 1604."""
        runs = re.findall(r"\d+", self.identifier or "")
        if not runs:
            return ""
        longest = max(len(r) for r in runs)
        return [r for r in runs if len(r) == longest][-1][-4:]


@dataclass
class Reading:
    """Everything the model (plus the checks) concluded about one email."""
    email_id: str
    about_holding: bool = False
    model_says_scam: bool = False
    scam_reasons: list[str] = field(default_factory=list)  # from code, not the model
    items: list[Item] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def is_scam(self) -> bool:
        return self.model_says_scam or bool(self.scam_reasons)


# JSON schema handed to Ollama's `format`, so Gemma can only answer in this shape.
OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "about_holding": {"type": "boolean"},
        "looks_like_scam": {"type": "boolean"},
        "items": {
            "type": "array",
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": KINDS},
                    "institution": {"type": "string"},
                    "identifier": {"type": ["string", "null"]},
                    "status": {"type": "string", "enum": STATUSES},
                    "evidence": {"type": "string"},
                },
                "required": ["kind", "institution", "identifier", "status", "evidence"],
            },
        },
    },
    "required": ["about_holding", "looks_like_scam", "items"],
}


def reading_to_dict(r: Reading) -> dict:
    from dataclasses import asdict
    return asdict(r)


def reading_from_dict(d: dict) -> Reading:
    return Reading(**{**d, "items": [Item(**it) for it in d.get("items", [])]})


def email_to_dict(e: Email) -> dict:
    return {"id": e.id, "subject": e.subject, "sender": e.sender, "date": e.date, "body": e.body}
