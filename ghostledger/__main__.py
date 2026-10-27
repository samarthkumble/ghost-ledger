"""Ghost Ledger command line.

  python -m ghostledger doctor
  python -m ghostledger scan  MAILBOX [--estate estate.yaml] [--out out] [--baseline]
  python -m ghostledger eval  [--mail data/estate/mails] [--truth data/estate/truth.yaml]
  python -m ghostledger letter N [--out out]

Durable mode (Temporal + Auth0):
  python -m ghostledger login                 sign in as the executor (Auth0)
  python -m ghostledger connect-gmail         put Gmail access in Auth0 Token Vault
  python -m ghostledger test-approval         send one Guardian push to your phone
  python -m ghostledger worker                run the Temporal worker (leave it running)
  python -m ghostledger start-scan MAILBOX    read the mailbox as a durable workflow
  python -m ghostledger claim 1 2 5           open claim workflows for holdings #1, #2, #5
  python -m ghostledger board [--watch]       see every claim's state (also out/claims.html)
  python -m ghostledger approve CLAIM_ID yes  (console approver only)
  python -m ghostledger replied CLAIM_ID "text"   mark a reply that came by post or phone
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from . import baseline, evaluate, gemma, ledger, letters, mailbox, pipeline, report
from .outputs import write_outputs
from .schema import reading_from_dict, reading_to_dict


def _estate(path: str) -> letters.Estate:
    return letters.Estate.from_dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def _progress(i: int, n: int, e) -> None:
    print(f"  [{i:>3}/{n}] {e.date[:10] if e.date else '':10}  {e.subject[:60]}", file=sys.stderr, flush=True)


def gemma_reader(model: str, cache: str):
    def read(e):
        t0 = time.perf_counter()
        r = gemma.read(e, model=model, cache_dir=cache)
        took = time.perf_counter() - t0
        found = ", ".join(f"{it.kind}:{it.last4 or '-'}" for it in r.items if it.ok) or "nothing"
        flag = " (retried)" if r.meta.get("retried") else ""
        print(f"        -> {found}{flag}  {took:.0f}s", file=sys.stderr, flush=True)
        return r
    return read


def cmd_scan(a) -> int:
    emails = mailbox.load(a.mailbox)
    est = _estate(a.estate)
    reader = baseline.read if a.baseline else gemma_reader(a.model, a.cache)
    if not a.baseline:
        msg = gemma.doctor(a.model)
        print(msg, file=sys.stderr)
        if msg.startswith("✗") and not a.cached:
            return 2
    print(f"{len(emails)} emails in {a.mailbox}", file=sys.stderr)
    scan = pipeline.run(emails, reader, _progress)
    holdings, ignored = write_outputs(Path(a.out), emails, scan, est, "regex baseline" if a.baseline else a.model)
    print(report.markdown(holdings, ignored, est, len(emails), scan.read_count,
                          "regex baseline" if a.baseline else a.model))
    print(f"\nWrote {a.out}/report.html, {a.out}/ledger.json and {a.out}/letters/", file=sys.stderr)
    return 0


def cmd_eval(a) -> int:
    emails = mailbox.load(a.mail)
    truth = evaluate.load_truth(a.truth)
    est = _estate(a.estate)
    full_ids = evaluate.full_identifiers(a.mail, truth)
    results, extra = {}, {}
    runs = [("regex baseline", baseline.read)]
    if not a.baseline_only:
        msg = gemma.doctor(a.model)
        print(msg, file=sys.stderr)
        if msg.startswith("✗") and not a.cached:
            return 2
        runs.append((a.model, gemma_reader(a.model, a.cache)))
    for name, reader in runs:
        print(f"\n== {name}", file=sys.stderr)
        t0 = time.perf_counter()
        scan = pipeline.run(emails, reader, _progress)
        holdings, ignored = ledger.build(emails, scan.readings, est.date_of_death)
        page = report.page(holdings, ignored, est, len(emails), scan.read_count, name)
        results[name] = evaluate.score(holdings, ignored, truth, page, full_ids)
        retried = sum(1 for r in scan.readings if r.meta.get("retried"))
        ms = [r.meta["ms"] for r in scan.readings if r.meta.get("ms")]
        extra[name] = {"emails_read": scan.read_count, "retried": retried,
                       "median_s_per_email": round(sorted(ms)[len(ms) // 2] / 1000, 1) if ms else None,
                       "wall_s": round(time.perf_counter() - t0)}
    print("\n" + evaluate.table(results))
    for name, r in results.items():
        print(f"\n{name}: missed {r['_missed']} invented {r['_invented']} duplicates {r['_duplicates']} wrong kind {r['_wrong_kind']} "
              f"wrong institution {r['_wrong_institution']} wrong status {r['_wrong_status']} leaks {r['_leaks']} {extra[name]}")
    name = Path(a.mail).resolve().parent.name  # "estate" or "estate2"
    Path("eval").mkdir(exist_ok=True)
    Path(f"eval/results-{name}.json").write_text(json.dumps({"results": results, "runs": extra}, indent=1), encoding="utf-8")
    Path(f"eval/results-{name}.md").write_text(evaluate.table(results) + "\n", encoding="utf-8")
    print(f"\nSaved eval/results-{name}.json", file=sys.stderr)
    return 0


def cmd_letter(a) -> int:
    data = json.loads((Path(a.out) / "ledger.json").read_text(encoding="utf-8"))
    h = data["holdings"][a.n - 1]
    print(json.dumps(h, indent=1))
    return 0


def cmd_auth(a) -> int:
    from . import auth0
    try:
        if a.cmd == "login":
            who = auth0.login()
            print(f"Signed in as {who.get('name') or who.get('email')} ({who.get('sub')}). Refresh token saved in .secrets/")
        elif a.cmd == "connect-gmail":
            done = auth0.connect_gmail()
            print(f"Gmail connected to Token Vault ({done.get('id')}), scopes: {', '.join(done.get('scopes') or [])}")
            print("Checking: getting a Gmail token from Token Vault ...", "ok" if auth0.google_token() else "failed")
        elif a.cmd == "test-approval":
            print("Check your phone (Auth0 Guardian) ...")
            print("Result:", auth0.approve_blocking("Ghost Ledger test: approve this"))
        else:
            print(json.dumps({k: v for k, v in auth0.load().items() if k != "refresh_token"}, indent=1))
    except auth0.AuthError as ex:
        print(f"✗ {ex}", file=sys.stderr)
        return 1
    return 0


def cmd_durable(a) -> int:
    import asyncio

    from . import config, durable
    if a.cmd == "worker":
        try:
            asyncio.run(durable.run_worker())
        except KeyboardInterrupt:
            print("Worker stopped. Workflows are safe and will continue when you start it again.")
    elif a.cmd == "start-scan":
        asyncio.run(durable.start_scan(a.mailbox, a.estate, a.out, a.model, a.cache, not a.no_follow))
    elif a.cmd == "claim":
        asyncio.run(durable.start_claims(a.numbers, a.out, a.estate, a.approver or config.APPROVER,
                                         a.day_seconds or config.DAY_SECONDS, a.wait_days))
    elif a.cmd == "board":
        async def loop():
            while True:
                await durable.board(a.out)
                if not a.watch:
                    return
                await asyncio.sleep(5)
                print("-" * 60)
        try:
            asyncio.run(loop())
        except KeyboardInterrupt:
            pass
    elif a.cmd == "approve":
        asyncio.run(durable.signal(a.workflow_id, "approve", "approved" if a.decision == "yes" else "denied"))
    elif a.cmd == "replied":
        asyncio.run(durable.signal(a.workflow_id, "replied", a.text))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ghostledger", description="Find what someone left behind, from their mailbox.")
    p.add_argument("--model", default=gemma.DEFAULT_MODEL)
    p.add_argument("--cache", default=".cache/gemma")
    p.add_argument("--estate", default="data/estate/estate.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    s = sub.add_parser("scan")
    s.add_argument("mailbox")
    s.add_argument("--out", default="out")
    s.add_argument("--baseline", action="store_true", help="regex only, no model")
    s.add_argument("--cached", action="store_true", help="use saved model answers without Ollama")
    e = sub.add_parser("eval")
    e.add_argument("--mail", default="data/estate/mails")
    e.add_argument("--truth", default="data/estate/truth.yaml")
    e.add_argument("--baseline-only", action="store_true")
    e.add_argument("--cached", action="store_true", help="re-score saved model answers without Ollama")
    l = sub.add_parser("letter")
    l.add_argument("n", type=int)
    l.add_argument("--out", default="out")
    sub.add_parser("login")
    sub.add_parser("connect-gmail")
    sub.add_parser("test-approval")
    sub.add_parser("whoami")
    sub.add_parser("worker")
    ss = sub.add_parser("start-scan")
    ss.add_argument("mailbox")
    ss.add_argument("--out", default="out")
    ss.add_argument("--no-follow", action="store_true")
    c = sub.add_parser("claim")
    c.add_argument("numbers", type=int, nargs="+")
    c.add_argument("--out", default="out")
    c.add_argument("--approver", default=None, choices=["guardian", "console"])
    c.add_argument("--day-seconds", type=int, default=None, help="length of one day; 86400 real, ~20 for a demo")
    c.add_argument("--wait-days", type=int, default=15)
    b = sub.add_parser("board")
    b.add_argument("--out", default="out")
    b.add_argument("--watch", action="store_true")
    ap = sub.add_parser("approve")
    ap.add_argument("workflow_id")
    ap.add_argument("decision", choices=["yes", "no"])
    rp = sub.add_parser("replied")
    rp.add_argument("workflow_id")
    rp.add_argument("text", nargs="?", default="")
    a = p.parse_args(argv)
    if a.cmd in ("login", "connect-gmail", "test-approval", "whoami"):
        return cmd_auth(a)
    if a.cmd in ("worker", "start-scan", "claim", "board", "approve", "replied"):
        return cmd_durable(a)
    if a.cmd == "doctor":
        print(gemma.doctor(a.model))
        return 0
    return {"scan": cmd_scan, "eval": cmd_eval, "letter": cmd_letter}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
