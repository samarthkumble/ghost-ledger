"""Check every item the model reports against the email it came from.

Rules, in plain words:
  1. The evidence sentence must really be in the email (word for word, ignoring spacing).
  2. The institution must be named in the email (body, subject or sender).
  3. An account-like identifier must really appear in the email. No identifier, no asset:
     a promotion that mentions "mutual fund" is not a folio. Subscriptions and utilities are the
     exception; a service name and a charge are enough.
  4. "closed" and "matured_unclaimed" are strong claims, so the evidence must say so.
"""
from __future__ import annotations

import re
import unicodedata

from .schema import Email, Item

NEEDS_NO_ID = {"subscription", "utility"}
CLOSED_WORDS = re.compile(r"\b(closed|closure|terminated|surrendered|paid out|settled)\b", re.I)
MATURED_WORDS = re.compile(r"\bmatur(ed|ity)\b", re.I)
UNCLAIMED_WORDS = re.compile(r"(unclaimed|unpaid|not been received|no renewal|awaiting|still unpaid|remained unclaimed|held as)", re.I)
FILLER = re.compile(r"\b(ltd|limited|pvt|private|co|company|the|india|of|and|insurance|bank|mutual|fund|securities|"
                    r"services|registrar|dept|department)\b")


def norm(text: str | None) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text).lower()
    t = t.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"}))
    t = re.sub(r"[*_|>]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def in_email(quote: str, e: Email) -> bool:
    q = norm(quote).strip(" .\"'")
    return bool(q) and q in norm(e.full_text)


def inst_tokens(name: str) -> list[str]:
    t = re.sub(r"[^a-z0-9 ]", " ", norm(name))
    return [w for w in re.sub(FILLER, " ", t).split() if len(w) > 2]


def institution_named(name: str, e: Email) -> bool:
    toks = inst_tokens(name)
    if not toks:
        return False
    hay = norm(e.full_text) + " " + e.sender_domain.replace(".", " ")
    return toks[0] in hay


def check(item: Item, e: Email) -> str | None:
    """None if the item is supported by the email, else a short reason (shown to the model on retry)."""
    if not in_email(item.evidence, e):
        return "the evidence is not copied word for word from the email"
    if not institution_named(item.institution, e):
        return f'"{item.institution}" is not named in the email'
    if item.kind not in NEEDS_NO_ID:
        if not item.identifier or len(item.last4) < 3:
            return "no account, policy, folio or other identifier: a mention is not a holding"
        if item.last4 not in re.sub(r"\D", "", e.full_text):
            return f'the identifier "{item.identifier}" does not appear in the email'
    return None


def settle_status(item: Item, e: Email | None = None) -> str:
    """Downgrade strong statuses the email doesn't support, rather than rejecting the item.

    The model quotes one sentence, but "matured on 14-06-2024." and "held as matured unclaimed deposit"
    are often neighbouring sentences, so the support is looked for in the whole email."""
    text = e.full_text if e is not None else item.evidence
    if item.status == "closed" and not CLOSED_WORDS.search(text):
        return "unknown"
    if item.status == "matured_unclaimed" and not (MATURED_WORDS.search(text) and UNCLAIMED_WORDS.search(text)):
        return "unknown" if not MATURED_WORDS.search(text) else "active"
    return item.status


DEMAT_WORDS = re.compile(r"\b(demat|dp id|client id|depository participant)\b", re.I)
PAYMENT_METHOD = re.compile(r"(auto-?pay|charged to|paid (by|with|via)|debited from)\b.{0,40}\bcard\b|\bcard ending\b.{0,40}\b(charged|auto-?pay)", re.I)


def normalize(items: list[Item], e: Email) -> list[Item]:
    """Fixed domain rules applied to what the model says, before grounding.

    - Shares the email says are held in a demat account are a demat holding, not physical shares.
    - A card that only appears as how a bill or subscription is paid is not a holding of the biller;
      the card itself shows up in its own issuer's statements.
    """
    out = []
    for it in items:
        if it.kind == "shares_physical" and DEMAT_WORDS.search(it.evidence):
            it.kind = "demat"
        if it.kind == "credit_card" and PAYMENT_METHOD.search(it.evidence) and not institution_issues_cards(it, e):
            continue
        out.append(it)
    return out


def institution_issues_cards(it: Item, e: Email) -> bool:
    """True when the email itself is from the card issuer (a card statement), not from a biller."""
    return bool(re.search(r"(card statement|statement for .{0,40}card|card services)", e.full_text, re.I))
