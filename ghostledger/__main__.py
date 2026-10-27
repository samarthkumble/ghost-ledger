"""Ghost Ledger command line.

  python -m ghostledger doctor
  python -m ghostledger scan  MAILBOX [--estate estate.yaml] [--out out] [--baseline]
  python -m ghostledger eval  [--mail data/estate/mails] [--truth data/estate/truth.yaml]
  python -m ghostledger letter N [--out out]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from . import baseline, evaluate, gemma, ledger, letters, mailbox, pipeline, report
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


def write_outputs(out: Path, emails, scan, est: letters.Estate, model: str) -> tuple[list, list]:
    holdings, ignored = ledger.build(emails, scan.readings, est.date_of_death)
    out.mkdir(parents=True, exist_ok=True)
    (out / "readings.json").write_text(json.dumps([reading_to_dict(r) for r in scan.readings], indent=1), encoding="utf-8")
    (out / "ledger.json").write_text(json.dumps({"estate": est.__dict__, "holdings": [h.to_dict() for h in holdings],
                                                 "ignored": ignored}, indent=1), encoding="utf-8")
    (out / "report.md").write_text(report.markdown(holdings, ignored, est, len(emails), scan.read_count, model), encoding="utf-8")
    (out / "report.html").write_text(report.page(holdings, ignored, est, len(emails), scan.read_count, model), encoding="utf-8")
    ldir = out / "letters"
    ldir.mkdir(exist_ok=True)
    for i, h in enumerate(holdings, 1):
        if letters.needs_letter(h):
            (ldir / f"{i:02d}-{h.kind}-{h.last4 or 'x'}.txt").write_text(
                f"Subject: {letters.subject(h, est)}\n\n{letters.body(h, est)}\n", encoding="utf-8")
    return holdings, ignored


def cmd_scan(a) -> int:
    emails = mailbox.load(a.mailbox)
    est = _estate(a.estate)
    reader = baseline.read if a.baseline else gemma_reader(a.model, a.cache)
    if not a.baseline:
        msg = gemma.doctor(a.model)
        print(msg, file=sys.stderr)
        if msg.startswith("✗"):
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
        if msg.startswith("✗"):
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
        print(f"\n{name}: missed {r['_missed']} invented {r['_invented']} wrong kind {r['_wrong_kind']} "
              f"wrong institution {r['_wrong_institution']} wrong status {r['_wrong_status']} leaks {r['_leaks']} {extra[name]}")
    Path("eval").mkdir(exist_ok=True)
    Path("eval/results.json").write_text(json.dumps({"results": results, "runs": extra}, indent=1), encoding="utf-8")
    Path("eval/results.md").write_text(evaluate.table(results) + "\n", encoding="utf-8")
    return 0


def cmd_letter(a) -> int:
    data = json.loads((Path(a.out) / "ledger.json").read_text(encoding="utf-8"))
    h = data["holdings"][a.n - 1]
    print(json.dumps(h, indent=1))
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
    e = sub.add_parser("eval")
    e.add_argument("--mail", default="data/estate/mails")
    e.add_argument("--truth", default="data/estate/truth.yaml")
    e.add_argument("--baseline-only", action="store_true")
    l = sub.add_parser("letter")
    l.add_argument("n", type=int)
    l.add_argument("--out", default="out")
    a = p.parse_args(argv)
    if a.cmd == "doctor":
        print(gemma.doctor(a.model))
        return 0
    return {"scan": cmd_scan, "eval": cmd_eval, "letter": cmd_letter}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
