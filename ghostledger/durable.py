"""CLI side of the Temporal workflows: run the worker, start scans and claims, show the claims board."""
from __future__ import annotations

import asyncio
import concurrent.futures
import html
import json
import re
from datetime import datetime
from pathlib import Path

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker

from . import config
from .activities import ALL
from .flows import ClaimFlow, EstateScan


async def client() -> Client:
    try:
        return await Client.connect(config.TEMPORAL_ADDRESS)
    except Exception as ex:
        raise SystemExit(f"Can't reach Temporal at {config.TEMPORAL_ADDRESS}. Start it in another window with:\n"
                         f"  temporal server start-dev --db-filename temporal.db\n({ex})")


async def run_worker() -> None:
    c = await client()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        w = Worker(c, task_queue=config.TASK_QUEUE, workflows=[EstateScan, ClaimFlow], activities=ALL,
                   activity_executor=pool, max_concurrent_activities=4)
        print(f"Worker running on task queue '{config.TASK_QUEUE}' (Temporal at {config.TEMPORAL_ADDRESS}). Ctrl+C to stop.")
        print("Stopping is safe: workflows wait, and continue when a worker is back.")
        await w.run()


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


async def start_scan(mailbox: str, estate: str, out: str, model: str, cache: str, follow: bool = True) -> None:
    c = await client()
    wid = f"estate-scan-{_slug(Path(mailbox).resolve().name)}"
    args = {"mailbox": str(Path(mailbox).resolve()), "estate": str(Path(estate).resolve()),
            "out": str(Path(out).resolve()), "model": model, "cache": str(Path(cache).resolve())}
    try:
        h = await c.start_workflow(EstateScan.run, args, id=wid, task_queue=config.TASK_QUEUE,
                                   id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE)
        print(f"Started {wid}. Watch it at http://localhost:8233/namespaces/default/workflows/{wid}")
    except WorkflowAlreadyStartedError:
        h = c.get_workflow_handle(wid)
        print(f"{wid} is already running; following it.")
    if not follow:
        return
    last = None
    while True:
        desc = await h.describe()
        if desc.status != WorkflowExecutionStatus.RUNNING:
            print(json.dumps(await h.result(), indent=1))
            return
        try:
            p = await h.query(EstateScan.progress)
            line = f"[{p['read']:>3}/{p['to_read']}] {p['stage']}: {p['current'][:70]}  ({p['items_found']} items so far)"
            if line != last:
                print(line, flush=True)
                last = line
        except Exception:
            pass
        await asyncio.sleep(3)


async def start_claims(numbers: list[int], out: str, estate: str, approver: str, day_seconds: int, wait_days: int) -> None:
    data = json.loads((Path(out) / "ledger.json").read_text(encoding="utf-8"))
    c = await client()
    for n in numbers:
        h = data["holdings"][n - 1]
        if h["status"] == "closed":
            print(f"#{n} {h['institution']} is closed; nothing to claim.")
            continue
        wid = f"claim-{_slug(h['institution'])}-{h['kind'].replace('_', '-')}-{h['identifier'][-4:] or 'x'}"
        args = {"holding": h, "estate": str(Path(estate).resolve()), "approver": approver,
                "day_seconds": day_seconds, "wait_days": wait_days}
        try:
            await c.start_workflow(ClaimFlow.run, args, id=wid, task_queue=config.TASK_QUEUE)
            print(f"#{n} started {wid}")
        except WorkflowAlreadyStartedError:
            print(f"#{n} {wid} is already running")


async def signal(wid: str, name: str, value: str) -> None:
    c = await client()
    h = c.get_workflow_handle(wid)
    await (h.signal(ClaimFlow.approve, value) if name == "approve" else h.signal(ClaimFlow.mark_replied, value))
    print(f"Sent {name}={value!r} to {wid}")


async def board(out: str, write_html: bool = True) -> None:
    c = await client()
    rows = []
    async for wf in c.list_workflows("WorkflowType = 'ClaimFlow'"):
        h = c.get_workflow_handle(wf.id, run_id=wf.run_id)
        try:
            st = await h.query(ClaimFlow.status)
        except Exception:
            st = {"state": wf.status.name.lower() if wf.status else "?", "events": []}
            if wf.status == WorkflowExecutionStatus.COMPLETED:
                res = await h.result()
                st = {"state": res.get("result", "done"), "events": res.get("events", [])}
        rows.append((wf.id, st, wf.start_time))
    rows.sort(key=lambda r: r[0])
    if not rows:
        print("No claims yet. Start some with: python -m ghostledger claim 1 2 3")
        return
    for wid, st, _ in rows:
        last = st["events"][-1]["text"] if st["events"] else ""
        print(f"{wid:58} {st['state'][:34]:34} {last[:70]}")
    if write_html:
        Path(out).mkdir(parents=True, exist_ok=True)
        cards = "".join(
            f"<section><h3>{html.escape(wid)}</h3><p class=s>{html.escape(st['state'])}</p><ol>"
            + "".join(f"<li><time>{html.escape(e['at'][11:19])}</time> {html.escape(e['text'])}</li>" for e in st["events"])
            + "</ol></section>" for wid, st, _ in rows)
        page = f"""<!doctype html><html><head><meta charset=utf-8><meta http-equiv=refresh content=5>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Ghost Ledger claims</title><style>
body{{margin:0;background:#f6f1e7;color:#2b2420;font:16px/1.5 Georgia,serif}}main{{max-width:980px;margin:0 auto;padding:32px 16px}}
section{{background:#fffaf1;border:1px solid #ddd2c0;border-left:4px solid #d9822b;border-radius:10px;padding:12px 16px;margin:12px 0}}
h3{{margin:0;font:600 15px ui-monospace,Consolas,monospace}}.s{{margin:4px 0;color:#b4442e;font-weight:600}}
ol{{margin:6px 0 0;padding-left:20px}}time{{font:13px ui-monospace,Consolas,monospace;color:#76695c;margin-right:6px}}
@media (prefers-color-scheme:dark){{body{{background:#1a1614;color:#efe6da}}section{{background:#221d1a;border-color:#3a322c}}}}
</style></head><body><main><h1>Claims in progress</h1><p>Updated {datetime.now():%H:%M:%S}. Each claim is a Temporal workflow.</p>{cards}</main></body></html>"""
        (Path(out) / "claims.html").write_text(page, encoding="utf-8")
