"""Temporal workflows. Settling an estate takes months; these keep going through crashes, reboots and silence.

EstateScan   reads a whole mailbox, one durable activity per email. Close the laptop halfway and it
             continues from the next unread email when the worker comes back.
ClaimFlow    one per holding: draft -> executor approves on her phone -> send from her Gmail -> wait
             (durable timer, checking for a reply each day) -> reminder after 15 days -> after the
             second reminder, draft a complaint to the regulator. A real claim waits weeks; Temporal
             holds that wait, not a cron job or a browser tab.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .activities import (DraftArgs, LedgerArgs, ReadArgs, ReplyArgs, SendArgs, ask_approval, build_ledger,
                             check_replies, draft_letter, read_email, send_letter, triage_mailbox)

PATIENT = RetryPolicy(initial_interval=timedelta(seconds=5), backoff_coefficient=2,
                      maximum_interval=timedelta(minutes=2))  # e.g. Ollama not running yet: keep trying
FEW = RetryPolicy(initial_interval=timedelta(seconds=5), maximum_attempts=3)


@workflow.defn
class EstateScan:
    def __init__(self) -> None:
        self.total = 0
        self.done = 0
        self.current = ""
        self.found = 0
        self.stage = "starting"

    @workflow.query
    def progress(self) -> dict:
        return {"stage": self.stage, "read": self.done, "to_read": self.total, "current": self.current,
                "items_found": self.found}

    @workflow.run
    async def run(self, args: dict) -> dict:
        self.stage = "triage"
        triaged = await workflow.execute_activity(triage_mailbox, args["mailbox"],
                                                  start_to_close_timeout=timedelta(minutes=2), retry_policy=FEW)
        todo = [t for t in triaged if t["verdict"] == "read"]
        self.total = len(todo)
        self.stage = "reading"
        readings = []
        for t in todo:
            self.current = f"{t['date']} {t['subject']}"
            r = await workflow.execute_activity(
                read_email, ReadArgs(args["mailbox"], t["id"], args["model"], args["cache"]),
                start_to_close_timeout=timedelta(minutes=15), heartbeat_timeout=timedelta(minutes=16),
                retry_policy=PATIENT, summary=t["subject"][:60])
            readings.append(r)
            self.done += 1
            self.found += sum(1 for it in r["items"] if it["ok"])
        self.stage = "building the map"
        result = await workflow.execute_activity(
            build_ledger, LedgerArgs(args["mailbox"], args["estate"], args["out"], args["model"], readings),
            start_to_close_timeout=timedelta(minutes=5), retry_policy=FEW)
        self.stage = "done"
        return {"emails": len(triaged), "read": len(todo), "skipped": sum(t["verdict"] == "skip" for t in triaged),
                "scams": sum(t["verdict"] == "scam" for t in triaged), "holdings": len(result["holdings"]),
                "out": result["out"]}


@workflow.defn
class ClaimFlow:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.state = "drafting"
        self.decision: str | None = None  # console approvals arrive as a signal
        self.reply: str | None = None
        self.letter: dict = {}

    # ---------------------------------------------------------------- outside world talks to the workflow
    @workflow.signal
    def approve(self, decision: str) -> None:
        self.decision = decision

    @workflow.signal
    def mark_replied(self, text: str) -> None:
        self.reply = text or "reply received"

    @workflow.query
    def status(self) -> dict:
        return {"state": self.state, "events": self.events, "subject": self.letter.get("subject", "")}

    def log(self, text: str) -> None:
        self.events.append({"at": workflow.now().isoformat(timespec="seconds"), "text": text})
        workflow.logger.info(text)

    # ---------------------------------------------------------------- steps
    async def get_approval(self, args: dict, what: str) -> str:
        self.state = f"waiting for approval: {what}"
        h = args["holding"]
        ref = h.get("identifier", "")[-4:]
        if args.get("approver", "guardian") == "console":
            self.decision = None
            self.log(f"Waiting for the executor to approve: {what}")
            await workflow.wait_condition(lambda: self.decision is not None)
            return self.decision or "denied"
        for attempt in range(3):
            self.log(f"Approval request sent to the executor's phone: {what}")
            res = await workflow.execute_activity(
                ask_approval, f"{what} {h['institution']} {ref}",
                start_to_close_timeout=timedelta(minutes=7), heartbeat_timeout=timedelta(minutes=1),
                retry_policy=FEW)
            if res in ("approved", "denied"):
                return res
            self.log("No answer on the phone within 5 minutes; asking again in a day")
            await workflow.sleep(timedelta(seconds=args["day_seconds"]))
        return "expired"

    async def wait_for_reply(self, args: dict, thread_id: str, our_ids: list[str], days: int) -> bool:
        for day in range(1, days + 1):
            self.state = f"waiting for a reply: day {day} of {days}"
            try:
                await workflow.wait_condition(lambda: self.reply is not None,
                                              timeout=timedelta(seconds=args["day_seconds"]), timeout_summary=f"day {day}")
            except asyncio.TimeoutError:
                pass
            if self.reply is not None:
                return True
            found = await workflow.execute_activity(check_replies, ReplyArgs(thread_id, our_ids),
                                                    start_to_close_timeout=timedelta(minutes=1), retry_policy=FEW)
            if found:
                self.reply = found[0].get("snippet") or "reply received"
                return True
        return False

    @workflow.run
    async def run(self, args: dict) -> dict:
        h = args["holding"]
        sent_on: list[str] = []
        our_ids: list[str] = []
        thread_id = in_reply_to = None
        self.log(f"Claim opened: {h['institution']} {h['kind'].replace('_', ' ')} {h.get('identifier', '')}")
        for n in range(3):  # the letter, then up to two reminders
            what = "Send claim letter to" if n == 0 else f"Send reminder {n} to"
            self.state = "drafting"
            self.letter = await workflow.execute_activity(draft_letter, DraftArgs(h, args["estate"], follow_up=n),
                                                          start_to_close_timeout=timedelta(minutes=1), retry_policy=FEW)
            decision = await self.get_approval(args, what)
            if decision != "approved":
                self.state = "stopped by the executor" if decision == "denied" else "paused: no approval"
                self.log(f"Not sent ({decision}). Nothing goes out without the executor's approval.")
                return {"result": self.state, "events": self.events}
            self.state = "sending"
            sent = await workflow.execute_activity(
                send_letter, SendArgs(self.letter["to"], self.letter["subject"], self.letter["body"], thread_id, in_reply_to),
                start_to_close_timeout=timedelta(minutes=2), retry_policy=FEW)
            thread_id, in_reply_to = sent["threadId"], sent.get("message_id") or in_reply_to
            our_ids.append(sent["id"])
            sent_on.append(workflow.now().date().isoformat())
            self.log(f"{'Letter' if n == 0 else f'Reminder {n}'} sent from the executor's Gmail to {sent['to']}")
            if await self.wait_for_reply(args, thread_id, our_ids, args.get("wait_days", 15)):
                self.state = "answered"
                self.log(f"The institution replied: {self.reply[:120]}")
                return {"result": "answered", "reply": self.reply, "events": self.events}
            self.log(f"No reply in {args.get('wait_days', 15)} days")
        self.state = "drafting complaint"
        esc = await workflow.execute_activity(draft_letter, DraftArgs(h, args["estate"], sent_on=sent_on, escalate=True),
                                              start_to_close_timeout=timedelta(minutes=1), retry_policy=FEW)
        self.letter = esc
        self.state = "escalate"
        self.log(f"Three letters, no answer. Complaint drafted for {esc['regulator']}: file it at {esc['portal']}")
        return {"result": "escalate", "complaint": esc, "events": self.events}
