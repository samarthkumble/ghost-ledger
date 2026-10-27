"""Read a mailbox: a folder of .eml files, or the .mbox that Google Takeout produces."""
from __future__ import annotations

import email
import email.policy
import email.utils
import hashlib
import mailbox
import re
from html.parser import HTMLParser
from pathlib import Path

from .schema import Email


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        if tag in ("br", "p", "div", "tr", "li", "h1", "h2", "h3", "table"):
            self.out.append("\n")
        elif tag in ("td", "th") and self.out and not self.out[-1].endswith("\n"):
            self.out.append(" | ")  # keep table cells apart: "Account Number | XXXX 6127"

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)


def html_to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    return re.sub(r"\n\s*\n+", "\n\n", "".join(p.out)).strip()


def _body(msg) -> str:
    if msg.is_multipart():
        plain = html = None
        for part in msg.walk():
            if part.get_content_maintype() == "multipart" or part.get_filename():
                continue
            ctype = part.get_content_type()
            try:
                text = part.get_content()
            except Exception:
                continue
            if ctype == "text/plain" and plain is None:
                plain = text
            elif ctype == "text/html" and html is None:
                html = text
        return plain if plain else html_to_text(html or "")
    try:
        text = msg.get_content()
    except Exception:
        text = msg.get_payload(decode=True).decode("utf-8", "replace")
    return html_to_text(text) if msg.get_content_type() == "text/html" else text


def _iso(date_header) -> str | None:
    try:
        return email.utils.parsedate_to_datetime(str(date_header)).isoformat()
    except Exception:
        return None


def from_message(msg, fallback_id: str | None = None) -> Email:
    subject = str(msg.get("Subject", "")).strip()
    body = _body(msg).strip()
    mid = fallback_id or hashlib.sha1(f"{subject}|{msg.get('Date')}|{body[:300]}".encode()).hexdigest()[:12]
    return Email(id=mid, subject=subject, sender=str(msg.get("From", "")), date=_iso(msg.get("Date")), body=body)


def load(path: str | Path) -> list[Email]:
    path = Path(path)
    out: list[Email] = []
    files = [path] if path.is_file() else sorted(path.rglob("*"))
    for f in files:
        if f.suffix.lower() == ".eml":
            msg = email.message_from_bytes(f.read_bytes(), policy=email.policy.default)
            out.append(from_message(msg, f.stem))
        elif f.suffix.lower() == ".mbox":
            for i, msg in enumerate(mailbox.mbox(str(f), factory=lambda fp: email.message_from_binary_file(fp, policy=email.policy.default))):
                out.append(from_message(msg))
    out.sort(key=lambda e: e.date or "")
    return out
