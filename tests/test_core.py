"""Ghost Ledger tests. No model needed: Ollama is replaced by scripted answers."""
import json
import re
from pathlib import Path

import pytest

from ghostledger import baseline, evaluate, gemma, grounding, ledger, letters, mailbox, pipeline, report
from ghostledger.schema import Email, Item, Reading

ROOT = Path(__file__).resolve().parents[1]
MAILS = ROOT / "data/estate/mails"
TRUTH = evaluate.load_truth(ROOT / "data/estate/truth.yaml")
EST = letters.Estate("Raghavendra Rao", "2026-06-21", "Ananya Rao", "daughter", "ananya.rao@mail.example")


@pytest.fixture(scope="module")
def emails():
    return mailbox.load(MAILS)


@pytest.fixture
def by_id(emails):
    return {e.id: e for e in emails}


def scripted(monkeypatch, answers):
    """Replace the Ollama call with a queue of JSON answers; returns the list of calls made."""
    calls = []

    def fake_chat(messages, model):
        calls.append(messages)
        return {"message": {"content": json.dumps(answers.pop(0))}, "eval_count": 10}

    monkeypatch.setattr(gemma, "_chat", fake_chat)
    return calls


def item(kind, inst, ident, status, evidence):
    return {"kind": kind, "institution": inst, "identifier": ident, "status": status, "evidence": evidence}


# ------------------------------------------------------------------ grounding
def test_invented_identifier_is_rejected_then_fixed_on_retry(monkeypatch, tmp_path, by_id):
    e = by_id["mal-fd-1"]
    ev = "Your Fixed Deposit Receipt No. MCB/FD/00417703 matured on 14-06-2024."
    calls = scripted(monkeypatch, [
        {"about_holding": True, "looks_like_scam": False, "items": [item("fixed_deposit", "Malnad Co-operative Bank", "MCB/FD/00419999", "matured_unclaimed", ev)]},
        {"about_holding": True, "looks_like_scam": False, "items": [item("fixed_deposit", "Malnad Co-operative Bank", "MCB/FD/00417703", "matured_unclaimed", ev)]},
    ])
    r = gemma.read(e, cache_dir=tmp_path)
    assert len(calls) == 2 and "does not appear in the email" in calls[1][-1]["content"]
    assert [(i.last4, i.ok) for i in r.items] == [("7703", True)]
    assert r.meta["retried"]


def test_unfixable_item_is_dropped_not_guessed(monkeypatch, tmp_path, by_id):
    e = by_id["mal-fd-1"]
    bad = item("fixed_deposit", "Malnad Co-operative Bank", "MCB/FD/00419999", "active", "Your FD of Rs. 9,99,999 is safe.")
    scripted(monkeypatch, [{"about_holding": True, "looks_like_scam": False, "items": [bad]}] * 2)
    r = gemma.read(e, cache_dir=tmp_path)
    assert r.items == [] and len(r.meta["rejected"]) == 2
    hs, _ = ledger.build([e], [r])
    assert hs == []


def test_promotion_naming_a_fund_is_not_a_holding(by_id):
    e = by_id["pro-0"]
    it = Item("loan", "Kaveri Bank", None, "active", "you are pre-approved for a personal loan up to Rs. 8,00,000")
    assert "identifier" in grounding.check(it, e)


def test_closed_needs_closing_words():
    it = Item("bank_account", "Coastal Bank", "2210", "closed", "your savings account ending 2210 is active")
    assert grounding.settle_status(it) == "unknown"
    it.evidence = "your savings account ending 2210 has been closed"
    assert grounding.settle_status(it) == "closed"


def test_cache_means_no_second_model_call(monkeypatch, tmp_path, by_id):
    e = by_id["kav-sb-1"]
    ans = {"about_holding": True, "looks_like_scam": False,
           "items": [item("bank_account", "Kaveri Bank", "XXXXXXX4821", "active", "Savings Account No. XXXXXXX4821")]}
    calls = scripted(monkeypatch, [ans, ans])
    gemma.read(e, cache_dir=tmp_path)
    r = gemma.read(e, cache_dir=tmp_path)
    assert len(calls) == 1 and r.items[0].last4 == "4821"


# ------------------------------------------------------------------ scams, closed accounts, masking
def test_scam_emails_never_reach_the_model(emails):
    seen = []
    scan = pipeline.run(emails, lambda e: seen.append(e.id) or Reading(e.id))
    assert not set(seen) & set(TRUTH["traps"]["scam_emails"])
    assert {r.email_id for r in scan.readings if r.is_scam} == set(TRUTH["traps"]["scam_emails"])


def test_closed_account_gets_no_letter(by_id):
    e = by_id["cst-sb-1"]
    it = Item("bank_account", "Coastal Bank", "2210", "closed", "your savings account ending 2210 has been closed")
    hs, _ = ledger.build([e], [Reading(e.id, items=[it])])
    assert hs[0].route["action"] == "NOTHING (closed)" and not letters.needs_letter(hs[0])


def test_mask_keeps_dates_and_amounts():
    assert ledger.mask("policy no. 812444471 due 28-01-2026 for Rs. 24,318.00") == "policy no. XXXXX4471 due 28-01-2026 for Rs. 24,318.00"


def test_same_demat_quoted_two_ways_is_one_holding(by_id):
    a, b = by_id["dmt-0"], by_id["dmt-div-0"]
    r1 = Reading(a.id, items=[Item("demat", "Bharat Securities", "IN301926 / XXXX6650", "active", "Demat account: Bharat Securities Ltd. - DP ID IN301926 Client ID XXXX6650")])
    r2 = Reading(b.id, items=[Item("demat", "Bharat Securities", "XXXX6650", "active", "Client ID XXXX6650.")])
    hs, _ = ledger.build([a, b], [r1, r2])
    assert len(hs) == 1 and len(hs[0].evidence) == 2


# ------------------------------------------------------------------ whole pipeline with a perfect reader
def oracle(e: Email) -> Reading:
    """Answers straight from the truth file: checks that ledger + grounding + eval agree on a perfect read."""
    meta = TRUTH["emails"].get(e.id, {})
    items = []
    for ref in meta.get("refs", []):
        t = TRUTH["items"][ref]
        ident = str(t.get("ident") or "")
        line = next((ln for ln in e.body.splitlines() if ident and ident in re.sub(r"\D", "", ln)), "")
        if not line:
            line = next(ln for ln in e.body.splitlines() if ln.strip())
        status = {"at_risk_iepf": "at_risk"}.get(t["status"], t["status"])
        if meta.get("kind") == "asset_closed" or t["status"] == "closed":
            status = "closed" if grounding.CLOSED_WORDS.search(line) else "active"
        it = Item(t["kind"], t["institution"], ident or None, status, line.strip())
        it.reason = grounding.check(it, e) or ""
        it.ok = not it.reason
        it.status = grounding.settle_status(it) if it.ok else it.status
        items.append(it)
    return Reading(e.id, about_holding=bool(items), items=items)


def test_perfect_reader_scores_perfectly(emails):
    scan = pipeline.run(emails, oracle)
    rejected = [(r.email_id, i.reason) for r in scan.readings for i in r.items if not i.ok]
    assert rejected == []
    hs, ign = ledger.build(emails, scan.readings, EST.date_of_death)
    page = report.page(hs, ign, EST, len(emails), scan.read_count)
    s = evaluate.score(hs, ign, TRUTH, page, evaluate.full_identifiers(MAILS, TRUTH))
    assert s["holdings_found"] == "15/15" and s["subscriptions_found"] == "5/5", s
    assert s["invented"] == 0 and s["closed_account_claimed"] == 0 and s["masking_leaks"] == 0, s
    assert s["flagged_statuses_correct"] == "5/5", s


def test_baseline_runs_and_is_scored(emails):
    scan = pipeline.run(emails, baseline.read)
    hs, ign = ledger.build(emails, scan.readings, EST.date_of_death)
    s = evaluate.score(hs, ign, TRUTH)
    assert s["scam_emails_used"] == 0 and s["closed_account_claimed"] == 0
