"""Workflow logic without a Temporal server: the workflow APIs are replaced by simple fakes.
(The real thing runs against `temporal server start-dev`; these check the decisions the workflow makes.)"""
import asyncio
import logging
from datetime import datetime, timedelta

import pytest
from temporalio import workflow

from ghostledger import activities, flows
from ghostledger.auth0 import binding_message

HOLDING = {"kind": "fixed_deposit", "institution": "Malnad Co-operative Bank", "identifier": "XXXX7703",
           "status": "matured_unclaimed", "evidence": [], "after_death": []}


class Fake:
    def __init__(self, approvals, replies_on_check=None):
        self.approvals = list(approvals)
        self.replies_on_check = replies_on_check  # check number at which a reply shows up
        self.checks = 0
        self.sent = []
        self.slept = []
        self.clock = datetime(2026, 7, 1, 10, 0, 0)

    async def execute_activity(self, fn, arg=None, **kw):
        if fn is activities.draft_letter:
            if arg.escalate:
                return {"to": "x@example", "subject": "Complaint", "body": "...", "portal": "https://cms.rbi.org.in",
                        "regulator": "RBI Integrated Ombudsman"}
            return {"to": "x@example", "subject": f"letter {arg.follow_up}", "body": "..."}
        if fn is activities.ask_approval:
            return self.approvals.pop(0)
        if fn is activities.send_letter:
            self.sent.append(arg)
            return {"id": f"m{len(self.sent)}", "threadId": "t1", "message_id": f"<m{len(self.sent)}>", "to": arg.to}
        if fn is activities.check_replies:
            self.checks += 1
            return [{"snippet": "Your claim ref is 123"}] if self.checks == self.replies_on_check else []
        raise AssertionError(fn)

    async def wait_condition(self, fn, timeout=None, timeout_summary=None):
        if fn():
            return
        if timeout is None:
            raise AssertionError("would wait forever")
        self.clock += timeout if isinstance(timeout, timedelta) else timedelta(seconds=timeout)
        raise asyncio.TimeoutError

    async def sleep(self, d):
        self.slept.append(d)
        self.clock += d


@pytest.fixture
def fake(monkeypatch):
    def make(**kw):
        f = Fake(**kw)
        monkeypatch.setattr(workflow, "execute_activity", f.execute_activity)
        monkeypatch.setattr(workflow, "wait_condition", f.wait_condition)
        monkeypatch.setattr(workflow, "sleep", f.sleep)
        monkeypatch.setattr(workflow, "now", lambda: f.clock)
        monkeypatch.setattr(workflow, "logger", logging.getLogger("wf"))
        return f
    return make


ARGS = {"holding": HOLDING, "estate": "e.yaml", "approver": "guardian", "day_seconds": 86400, "wait_days": 15}


def test_reply_on_day_3_ends_the_claim(fake):
    f = fake(approvals=["approved"], replies_on_check=3)
    res = asyncio.run(flows.ClaimFlow().run(ARGS))
    assert res["result"] == "answered" and len(f.sent) == 1 and f.checks == 3


def test_silence_means_two_reminders_then_a_complaint(fake):
    f = fake(approvals=["approved"] * 3)
    res = asyncio.run(flows.ClaimFlow().run(ARGS))
    assert res["result"] == "escalate" and len(f.sent) == 3
    assert [s.thread_id for s in f.sent] == [None, "t1", "t1"]  # reminders stay in the same thread
    assert f.clock - datetime(2026, 7, 1, 10) == timedelta(days=45)
    assert "RBI" in res["complaint"]["regulator"]


def test_denied_on_the_phone_sends_nothing(fake):
    f = fake(approvals=["denied"])
    res = asyncio.run(flows.ClaimFlow().run(ARGS))
    assert res["result"] == "stopped by the executor" and f.sent == []


def test_unanswered_push_is_asked_again_next_day(fake):
    f = fake(approvals=["expired", "approved"], replies_on_check=1)
    res = asyncio.run(flows.ClaimFlow().run(ARGS))
    assert res["result"] == "answered" and f.slept == [timedelta(days=1)]


def test_binding_message_is_what_auth0_accepts():
    m = binding_message("Send claim letter to Malnad Co-operative Bank (FD) 7703!")
    assert len(m) <= 64 and "(" not in m and "!" not in m


def test_estate_scan_runs_every_activity_for_real(monkeypatch, tmp_path):
    """EstateScan with the real activities (Gemma swapped for the regex baseline)."""
    from pathlib import Path

    from temporalio import activity

    from ghostledger import baseline, gemma
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(activity, "heartbeat", lambda *a: None)
    monkeypatch.setattr(gemma, "read", lambda e, **kw: baseline.read(e))

    async def run_now(fn, arg=None, **kw):
        return fn(arg)
    monkeypatch.setattr(workflow, "execute_activity", run_now)
    wf = flows.EstateScan()
    res = asyncio.run(wf.run({"mailbox": str(root / "data/estate/mails"), "estate": str(root / "data/estate/estate.yaml"),
                              "out": str(tmp_path), "model": "test", "cache": str(tmp_path / "c")}))
    assert res["emails"] == 75 and res["scams"] == 6 and res["holdings"] > 10
    assert (tmp_path / "report.html").exists() and wf.progress()["stage"] == "done"
