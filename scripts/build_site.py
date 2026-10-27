"""Fill site/template.html with the real eval numbers and copy the demo report. Output: site/dist/."""
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKS = {"REPO_URL": "https://github.com/samarthkumble/ghost-ledger", "DEMO_URL": "demo/report.html",
         "VIDEO_URL": "", "POST_URL": "", "LICENSE": "MIT"}
LABELS = [("holdings_found", "Holdings found (of 15)"), ("subscriptions_found", "Subscriptions and bills found (of 5)"),
          ("invented", "Holdings invented"), ("wrong_institution", "Filed under the wrong institution"),
          ("wrong_kind", "Filed as the wrong kind"), ("flagged_statuses_correct", "Matured / at-risk / inoperative caught (of 5)"),
          ("closed_account_claimed", "Closed account put on the claim list"), ("scam_emails_used", "Scam emails used as evidence"),
          ("masking_leaks", "Full account numbers leaked in the report")]
KEY = {"holdings_found", "invented", "closed_account_claimed", "scam_emails_used"}


def _cell(res: dict, name: str, key: str) -> str:
    return html.escape(str(res.get(name, {}).get(key, "–")).split("/")[0]) if name in res else "–"


def main(report_dir: str = "out", **links):
    import os
    links = {**{k: os.environ[k] for k in ("VIDEO_URL", "POST_URL", "REPO_URL") if os.environ.get(k)}, **links}
    LINKS.update(links)
    tuned = json.loads((ROOT / "eval/results-estate.json").read_text(encoding="utf-8"))
    held = json.loads((ROOT / "eval/results-estate2.json").read_text(encoding="utf-8"))
    g = next((n for n in tuned["results"] if "gemma" in n), None)
    b = "regex baseline"
    rows_def = [("holdings_found", "Holdings and debts found", "15", "13"),
                ("subscriptions_found", "Subscriptions and bills found", "5", "4"),
                ("flagged_statuses_correct", "Matured / at-risk / dormant / closed caught", "5", "4"),
                ("invented", "Invented entries", "", ""), ("duplicates", "Duplicate entries", "", ""),
                ("wrong_kind", "Filed as the wrong kind", "", ""), ("wrong_institution", "Filed under the wrong institution", "", ""),
                ("closed_account_claimed", "Closed account put on the claim list", "", ""),
                ("scam_emails_used", "Scam emails used as evidence", "", ""),
                ("masking_leaks", "Full account numbers in the report", "", "")]
    key_rows = {"holdings_found", "invented", "closed_account_claimed", "scam_emails_used"}
    head = ("<tr><th rowspan=2>Metric</th><th colspan=2 class=n>Raghavendra, 75 emails<br><small>rules fixed after run 1</small></th>"
            "<th colspan=2 class=n>Leela, 47 emails<br><small>held out, never tuned on</small></th></tr>"
            f"<tr><th class=n>Regex</th><th class=n>{html.escape(g or 'Gemma')}</th><th class=n>Regex</th><th class=n>{html.escape(g or 'Gemma')}</th></tr>")
    body = ""
    for k, label, n1, n2 in rows_def:
        cells = [_cell(tuned["results"], b, k), _cell(tuned["results"], g, k), _cell(held["results"], b, k), _cell(held["results"], g, k)]
        if n1:
            cells = [f"{cells[0]} / {n1}", f"{cells[1]} / {n1}", f"{cells[2]} / {n2}", f"{cells[3]} / {n2}"]
        body += f"<tr{' class=key' if k in key_rows else ''}><td>{html.escape(label)}</td>" + "".join(f"<td class=n>{c}</td>" for c in cells) + "</tr>"
    table = f"<div class=tablewrap><table><thead>{head}</thead><tbody>{body}</tbody></table></div>"
    r1, r2 = tuned["runs"].get(g, {}), held["runs"].get(g, {})
    note = (f"Gemma 4 E4B read {r1.get('emails_read')} + {r2.get('emails_read')} emails on a Ryzen 5 5500U laptop CPU "
            f"(median {r1.get('median_s_per_email')} s and {r2.get('median_s_per_email')} s per email). "
            "Its one held-out mistake: a metro trip receipt paid by card became a utility bill. The first run on Raghavendra's "
            "mailbox had one invented holding, one wrong kind and one missed 'matured' flag; those came from my checking code, "
            "fixed before the held-out estate was written and frozen. Reproduce: python -m ghostledger eval.")
    gh = held["results"][g]
    left = f"{str(gh['holdings_found']).split('/')[0]} of 13 found on a held-out mailbox"
    right = f"{gh['invented']} false entry" if gh["invented"] == 1 else f"{gh['invented']} false entries"
    video = LINKS["VIDEO_URL"]
    fill = {**LINKS, "VIDEO_URL": video or "#how", "VIDEO_LABEL": "Watch the demo" if video else "See how it works",
            "POST_LINK": f' · <a href="{LINKS["POST_URL"]}">Write-up</a>' if LINKS["POST_URL"] else "",
            "EVAL_TABLE": table, "EVAL_NOTE": html.escape(note), "TOTAL_LEFT": left, "TOTAL_RIGHT": right}
    page = (ROOT / "site/template.html").read_text(encoding="utf-8")
    for k, v in fill.items():
        page = page.replace("{{" + k + "}}", v)
    assert "{{" not in page, page[page.index("{{"):page.index("{{") + 40]
    dist = ROOT / "site/dist"
    (dist / "demo").mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(page, encoding="utf-8")
    shutil.copy(ROOT / report_dir / "report.html", dist / "demo/report.html")
    print("built", dist)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["out"]))
