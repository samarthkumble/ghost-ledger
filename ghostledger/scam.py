"""Code-side scam checks. These run whatever the model says.

A grieving family is exactly who scammers target ("unclaimed units in your father's name, 15% fee").
An asset is never taken from an email that fails these checks; the email is listed separately so the
family can see what was ignored and why.
"""
from __future__ import annotations

import re

from .schema import Email

FREE_MAIL = re.compile(r"(^|\.)(gmail|yahoo|outlook|hotmail|rediffmail|freemail|proton|aol)\.", re.I)
PRESSURE = [
    (r"will be (blocked|suspended|deactivated|disconnected)", "threatens to block or disconnect"),
    (r"within 24 hours|immediately|tonight", "manufactured urgency"),
    (r"processing fee|service fee|refundable fee|send rs\.?\s*[\d,]+", "asks for a fee to release money"),
    (r"lucky draw|you have won|congratulations!", "prize or lottery"),
    (r"reply with your (aadhaar|pan|bank|card)|submit your (bank )?card details|share (your )?otp", "asks for identity or card details"),
    (r"call our (officer|agent)", "asks you to call an 'officer'"),
]
LINK = re.compile(r"https?://([a-z0-9.-]+)", re.I)


def _root(domain: str) -> str:
    parts = domain.lower().strip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def check(e: Email) -> list[str]:
    reasons: list[str] = []
    text = f"{e.subject}\n{e.body}".lower()
    dom = e.sender_domain
    display = e.sender.split("<")[0].lower()
    institutional = re.search(r"\b(bank|insurance|life|mutual fund|mf|kyc|tax|refund|board|epf|pension)\b", display)
    if institutional and FREE_MAIL.search(dom):
        reasons.append(f"claims to be an institution but writes from a free-mail address ({dom})")
    for pattern, why in PRESSURE:
        if re.search(pattern, text):
            reasons.append(why)
    for link_dom in LINK.findall(e.body):
        if dom and _root(link_dom) != _root(dom):
            reasons.append(f"link goes to a different site ({link_dom})")
            break
    # urgency on its own is weak (real banks say "immediately" too); require two signals,
    # or one of the strong ones.
    strong = {"asks for a fee to release money", "prize or lottery", "asks for identity or card details",
              "asks you to call an 'officer'"}
    if any(r.startswith("claims to be") or r.startswith("link goes") for r in reasons) or strong & set(reasons):
        return reasons
    return reasons if len(reasons) >= 2 else []
