"""Score an inheritance map against the hand-written truth for the synthetic estate.

What matters, in order:
  1. invented holdings: 0. A family chasing a policy that doesn't exist loses weeks and trust.
  2. the closed account is NOT on the claim list; the scam emails produced nothing.
  3. holdings found, with the right kind and the right status (matured-unclaimed, at risk of IEPF).
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

from .grounding import inst_tokens
from .ledger import Holding

STATUS_MAP = {"at_risk_iepf": "at_risk"}


def load_truth(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _tok(name: str) -> str:
    t = inst_tokens(name)
    return t[0] if t else name.lower()


def _ids(tid: str, t: dict) -> set[str]:
    ident = str(t.get("ident") or "")
    return ({ident} if ident else set()) | {str(a) for a in t.get("alt", [])}


def _same_inst(a: str, b: str) -> bool:
    ta, tb = _tok(a), _tok(b)
    return ta.startswith(tb) or tb.startswith(ta)


def match(holdings: list[Holding], truth: dict) -> dict:
    """found: right institution, identifier and kind. wrong_kind / wrong_institution: a real holding, misfiled.
    invented: points at nothing in the truth."""
    items = truth["items"]
    found: dict[str, Holding] = {}
    wrong_kind: dict[str, Holding] = {}
    wrong_inst: dict[str, Holding] = {}
    invented: list[Holding] = []

    def id_ok(tid: str, t: dict, h: Holding) -> bool:
        ids = _ids(tid, t)
        if not ids or not h.last4:
            return not h.last4 or not ids and t["kind"] == h.kind
        return h.last4 in ids or any(i in d for i in ids for d in h.idents)

    for h in holdings:
        by_id = [(tid, t) for tid, t in items.items() if id_ok(tid, t, h)]
        both = [(tid, t) for tid, t in by_id if _same_inst(t["institution"], h.institution)]
        exact = [tid for tid, t in both if t["kind"] == h.kind]
        if exact:
            tid = next((x for x in exact if x not in found), exact[0])
            found.setdefault(tid, h)
        elif both:
            wrong_kind.setdefault(both[0][0], h)
        elif [tid for tid, t in by_id if t["kind"] == h.kind]:
            wrong_inst.setdefault([tid for tid, t in by_id if t["kind"] == h.kind][0], h)
        else:
            invented.append(h)
    return {"found": found, "wrong_kind": wrong_kind, "wrong_institution": wrong_inst, "invented": invented}


def full_identifiers(mail_dir: str | Path, truth: dict) -> set[str]:
    """Every full-length account number in the mailbox; none may appear in a published report."""
    idents = {str(t["ident"]) for t in truth["items"].values() if t.get("ident")}
    out = set()
    for f in Path(mail_dir).glob("*.eml"):
        for tok in re.findall(r"[A-Z0-9/]*\d{6,}", f.read_text(encoding="utf-8", errors="ignore")):
            digits = re.sub(r"\D", "", tok)
            if any(digits.endswith(i) for i in idents) and len(digits) >= 6:
                out.add(re.sub(r"^\D+", "", tok))
    return out


def score(holdings: list[Holding], ignored: list[dict], truth: dict, report_text: str = "",
          full_ids: set[str] | None = None) -> dict:
    m = match(holdings, truth)
    items = truth["items"]
    traps = truth["traps"]
    by_email = defaultdict(list)
    for h in holdings:
        for ev in h.evidence:
            by_email[ev["email"]].append(h)
    real_assets = [tid for tid, t in items.items() if t["kind"] not in ("subscription", "utility")]
    status_ok = [tid for tid, h in m["found"].items()
                 if h.status == STATUS_MAP.get(items[tid]["status"], items[tid]["status"])]
    flagged = {tid: items[tid]["status"] for tid in items if items[tid]["status"] not in ("active",)}
    closed_claimed = [tid for tid in traps["closed"] if tid in m["found"] and m["found"][tid].status != "closed"]
    leaks = sorted(i for i in (full_ids or set()) if i in report_text) if report_text else []
    return {
        "holdings_found": f"{sum(t in m['found'] for t in real_assets)}/{len(real_assets)}",
        "subscriptions_found": f"{sum(t in m['found'] for t in items if t not in real_assets)}/{len(items) - len(real_assets)}",
        "invented": len(m["invented"]),
        "wrong_kind": len(m["wrong_kind"]),
        "wrong_institution": len(m["wrong_institution"]),
        "status_correct": f"{len(status_ok)}/{len(m['found'])}",
        "flagged_statuses_correct": f"{sum(t in status_ok for t in flagged)}/{len(flagged)}",
        "closed_account_claimed": len(closed_claimed),
        "scam_emails_used": sum(1 for s in traps["scam_emails"] if by_email.get(s)),
        "promo_emails_used": sum(1 for p in traps["promo_emails"] if by_email.get(p)),
        "masking_leaks": len(leaks),
        "_missed": sorted(t for t in items if t not in m["found"]),
        "_invented": [f"{h.kind} {h.institution} {h.last4}" for h in m["invented"]],
        "_wrong_kind": {t: h.kind for t, h in m["wrong_kind"].items()},
        "_wrong_institution": {t: h.institution for t, h in m["wrong_institution"].items()},
        "_wrong_status": {t: f"{m['found'][t].status} (truth {items[t]['status']})" for t in m["found"] if t not in status_ok},
        "_leaks": leaks,
    }


def table(results: dict[str, dict]) -> str:
    rows = ["holdings_found", "subscriptions_found", "invented", "wrong_kind", "wrong_institution", "status_correct",
            "flagged_statuses_correct", "closed_account_claimed", "scam_emails_used", "promo_emails_used", "masking_leaks"]
    names = list(results)
    out = ["| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for r in rows:
        out.append(f"| {r.replace('_', ' ')} | " + " | ".join(str(results[n][r]) for n in names) + " |")
    return "\n".join(out)
