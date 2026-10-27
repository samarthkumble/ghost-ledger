"""Send letters and look for replies with the Gmail API, using a short-lived token from Auth0 Token Vault.

`outbox` mode writes .eml files instead, so the whole flow runs without any accounts.
"""
from __future__ import annotations

import base64
import time
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import requests

from . import auth0, config

API = "https://gmail.googleapis.com/gmail/v1/users/me"


def _h() -> dict:
    return {"Authorization": f"Bearer {auth0.google_token()}"}


def send(to: str, subject: str, body: str, thread_id: str | None = None, in_reply_to: str | None = None) -> dict:
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject if not in_reply_to else ("Re: " + subject if not subject.startswith("Re:") else subject)
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)
    if config.SENDER == "outbox":
        out = Path("out/outbox")
        out.mkdir(parents=True, exist_ok=True)
        mid = make_msgid(domain="ghostledger.local")
        msg["Message-ID"] = mid
        name = f"{int(time.time())}-{subject[:40].replace(' ', '_').replace('/', '-')}.eml"
        (out / name).write_bytes(bytes(msg))
        return {"id": name, "threadId": thread_id or name, "message_id": mid, "to": to}
    raw = base64.urlsafe_b64encode(bytes(msg)).decode()
    payload = {"raw": raw, **({"threadId": thread_id} if thread_id else {})}
    r = requests.post(f"{API}/messages/send", json=payload, headers=_h(), timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Gmail send failed ({r.status_code}): {r.text[:300]}")
    sent = r.json()
    meta = requests.get(f"{API}/messages/{sent['id']}", params={"format": "metadata", "metadataHeaders": "Message-ID"},
                        headers=_h(), timeout=30).json()
    mid = next((h["value"] for h in meta.get("payload", {}).get("headers", []) if h["name"].lower() == "message-id"), None)
    return {"id": sent["id"], "threadId": sent["threadId"], "message_id": mid, "to": to}


def replies(thread_id: str, our_ids: list[str]) -> list[dict]:
    """Messages in the thread that we didn't send: the institution's answers."""
    if config.SENDER == "outbox":
        inbox = Path("out/inbox") / f"{thread_id}.txt"
        return [{"id": inbox.name, "snippet": inbox.read_text(encoding="utf-8")[:200]}] if inbox.exists() else []
    r = requests.get(f"{API}/threads/{thread_id}", params={"format": "metadata", "metadataHeaders": ["From", "Subject"]},
                     headers=_h(), timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Gmail read failed ({r.status_code}): {r.text[:300]}")
    msgs = r.json().get("messages", [])
    return [{"id": m["id"], "snippet": m.get("snippet", ""),
             "from": next((h["value"] for h in m["payload"]["headers"] if h["name"] == "From"), "")}
            for m in msgs if m["id"] not in our_ids]
