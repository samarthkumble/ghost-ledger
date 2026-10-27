"""Temporal activities: every step that touches the outside world (the model, Gmail, Auth0, files).

Each one is safe to retry. Gemma answers are cached per email, so a retried read is free, and a crashed
worker only loses the email that was in flight.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from temporalio import activity
from temporalio.exceptions import ApplicationError

from . import auth0, config, gemma, gmail, letters, mailbox, pipeline
from .ledger import Holding
from .outputs import write_outputs
from .schema import email_to_dict, reading_from_dict, reading_to_dict

_MAILBOXES: dict[str, dict] = {}


def _mail(path: str) -> dict:
    if path not in _MAILBOXES:
        _MAILBOXES[path] = {e.id: e for e in mailbox.load(path)}
    return _MAILBOXES[path]


def _estate(path: str) -> letters.Estate:
    return letters.Estate.from_dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


# ------------------------------------------------------------------ scan
@activity.defn
def triage_mailbox(mailbox_path: str) -> list[dict]:
    out = []
    for e in _mail(mailbox_path).values():
        verdict, why = pipeline.triage(e)
        out.append({"id": e.id, "verdict": verdict, "why": why, "subject": e.subject, "date": (e.date or "")[:10]})
    return out


@dataclass
class ReadArgs:
    mailbox: str
    email_id: str
    model: str
    cache: str


@activity.defn
def read_email(a: ReadArgs) -> dict:
    e = _mail(a.mailbox)[a.email_id]
    activity.heartbeat(a.email_id)
    try:
        r = gemma.read(e, model=a.model, cache_dir=a.cache)
    except gemma.OllamaError as ex:
        raise ApplicationError(str(ex), type="OllamaDown")  # retried with backoff until Ollama is back
    return reading_to_dict(r)


@dataclass
class LedgerArgs:
    mailbox: str
    estate: str
    out: str
    model: str
    readings: list[dict]


@activity.defn
def build_ledger(a: LedgerArgs) -> dict:
    emails = list(_mail(a.mailbox).values())
    scan = pipeline.Scan(emails, [reading_from_dict(r) for r in a.readings])
    for e in emails:
        if pipeline.triage(e)[0] == "scam" and not any(r.email_id == e.id for r in scan.readings):
            scan.readings.append(pipeline.scam_reading(e))
    holdings, ignored = write_outputs(Path(a.out), emails, scan, _estate(a.estate), a.model)
    return {"holdings": [h.to_dict() for h in holdings], "ignored": len(ignored), "out": a.out}


# ------------------------------------------------------------------ claims
@dataclass
class DraftArgs:
    holding: dict
    estate: str
    follow_up: int = 0
    sent_on: list[str] | None = None
    escalate: bool = False


@activity.defn
def draft_letter(a: DraftArgs) -> dict:
    h, est = Holding.from_dict(a.holding), _estate(a.estate)
    to = config.DEMO_TO or ""
    if to and "@" in to and "+" not in to:
        user, dom = to.split("@", 1)
        tag = "".join(ch for ch in h.institution.lower() if ch.isalnum())[:20]
        to = f"{user}+{tag}@{dom}"
    if a.escalate:
        esc = letters.escalation(h, est, a.sent_on or [])
        return {"to": to, "subject": esc["subject"], "body": esc["body"], "portal": esc["to_portal"],
                "regulator": esc["regulator"]}
    return {"to": to, "subject": letters.subject(h, est), "body": letters.body(h, est, date.today(), a.follow_up)}


@activity.defn
def ask_approval(text: str) -> str:
    """Guardian push on the executor's phone. Blocks until she taps Approve / Deny, or 5 minutes pass."""
    try:
        return auth0.approve_blocking(text, expiry_s=300, heartbeat=lambda rid: activity.heartbeat(rid))
    except auth0.AuthError as ex:
        raise ApplicationError(str(ex), type="AuthError", non_retryable="Not signed in" in str(ex))


@dataclass
class SendArgs:
    to: str
    subject: str
    body: str
    thread_id: str | None = None
    in_reply_to: str | None = None


@activity.defn
def send_letter(a: SendArgs) -> dict:
    if not a.to:
        raise ApplicationError("No recipient. Set GHOST_DEMO_TO in .env (the demo estate's banks are fictional).",
                               non_retryable=True)
    return gmail.send(a.to, a.subject, a.body, a.thread_id, a.in_reply_to)


@dataclass
class ReplyArgs:
    thread_id: str
    our_ids: list[str]


@activity.defn
def check_replies(a: ReplyArgs) -> list[dict]:
    return gmail.replies(a.thread_id, a.our_ids)


ALL = [triage_mailbox, read_email, build_ledger, draft_letter, ask_approval, send_letter, check_replies]


def _debug_dump(x) -> str:  # handy when running activities by hand
    return json.dumps(x, indent=1, default=str)


__all__ = ["ALL", "ReadArgs", "LedgerArgs", "DraftArgs", "SendArgs", "ReplyArgs", "email_to_dict"]
