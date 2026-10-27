"""Fill site/template.html with the real eval numbers and copy the demo report. Output: site/dist/."""
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKS = {"REPO_URL": "https://github.com/samarthkumble/ghost-ledger", "DEMO_URL": "demo/report.html",
         "VIDEO_URL": "#", "POST_URL": "#", "LICENSE": "MIT"}
LABELS = [("holdings_found", "Holdings found (of 15)"), ("subscriptions_found", "Subscriptions and bills found (of 5)"),
          ("invented", "Holdings invented"), ("wrong_institution", "Filed under the wrong institution"),
          ("wrong_kind", "Filed as the wrong kind"), ("flagged_statuses_correct", "Matured / at-risk / inoperative caught (of 5)"),
          ("closed_account_claimed", "Closed account put on the claim list"), ("scam_emails_used", "Scam emails used as evidence"),
          ("masking_leaks", "Full account numbers leaked in the report")]
KEY = {"holdings_found", "invented", "closed_account_claimed", "scam_emails_used"}


def main(report_dir: str = "out", **links):
    LINKS.update(links)
    data = json.loads((ROOT / "eval/results.json").read_text(encoding="utf-8"))
    res, runs = data["results"], data.get("runs", {})
    names = list(res)
    head = "".join(f"<th class=n>{html.escape(n)}</th>" for n in names)
    rows = "".join(f"<tr{' class=key' if k in KEY else ''}><td>{html.escape(lbl)}</td>"
                   + "".join(f"<td class=n>{html.escape(str(res[n][k]).split('/')[0])}</td>" for n in names) + "</tr>"
                   for k, lbl in LABELS)
    table = f"<table><thead><tr><th>On 75 emails</th>{head}</tr></thead><tbody>{rows}</tbody></table>"
    g = next((n for n in names if "gemma" in n), names[-1])
    r = runs.get(g, {})
    note = (f"{g} read {r.get('emails_read', '?')} emails at a median {r.get('median_s_per_email', '?')} s each on a "
            f"Ryzen 5 5500U laptop CPU; {r.get('retried', 0)} needed a retry after the checks rejected something. "
            "Truth, scoring and both runs are in the repo: python -m ghostledger eval.")
    gh = res[g]
    fill = {**LINKS, "EVAL_TABLE": table, "EVAL_NOTE": html.escape(note),
            "G_HOLDINGS": str(gh["holdings_found"]).split("/")[0], "G_SCAMS": "6"}
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
