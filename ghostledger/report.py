"""The inheritance map, as Markdown (for the terminal / repo) and as one self-contained HTML page."""
from __future__ import annotations

import html
from datetime import date

from .ledger import Holding, mask
from .letters import KIND_WORDS, Estate

STATUS_WORDS = {"active": "active", "closed": "closed", "matured_unclaimed": "matured, never paid out",
                "inoperative": "inoperative", "at_risk": "at risk of transfer to IEPF", "unknown": "status not stated"}


def summary(holdings: list[Holding], ignored: list[dict], est: Estate, n_emails: int, n_read: int) -> dict:
    claims = [h for h in holdings if h.route["action"].startswith("CLAIM")]
    return {
        "emails": n_emails, "read": n_read, "holdings": len([h for h in holdings if h.status != "closed"]),
        "claims": len(claims),
        "urgent": len([h for h in holdings if h.status in ("matured_unclaimed", "at_risk", "inoperative")]),
        "still_charging": len([h for h in holdings if h.after_death and h.kind in ("subscription", "credit_card", "utility")]),
        "closed": len([h for h in holdings if h.status == "closed"]), "scams": len(ignored),
    }


def markdown(holdings: list[Holding], ignored: list[dict], est: Estate, n_emails: int, n_read: int,
             model: str = "gemma4:e4b") -> str:
    s = summary(holdings, ignored, est, n_emails, n_read)
    out = [f"# What {est.deceased} left behind", "",
           f"{s['emails']} emails scanned, {s['read']} read by {model} on this computer. "
           f"{s['holdings']} holdings found, {s['claims']} to claim, {s['urgent']} need attention first, "
           f"{s['still_charging']} still charging after {est.date_of_death}, {s['scams']} scam emails ignored.", ""]
    out += ["| # | Do this | What | Where | Ref | Status | Last email | Evidence |", "|---|---|---|---|---|---|---|---|"]
    for i, h in enumerate(holdings, 1):
        ev = h.evidence[-1]
        out.append(f"| {i} | {h.route['action']} | {KIND_WORDS.get(h.kind, h.kind)} | {h.institution} | "
                   f"{'XXXX' + h.last4 if h.last4 else '-'} | {STATUS_WORDS.get(h.status, h.status)} | {h.last_seen} | "
                   f"\"{mask(ev['quote'])}\" ({ev['date']}) |")
    if ignored:
        out += ["", "## Ignored: looked like scams", ""]
        out += [f"- {x['date']} \"{x['subject']}\" from {x['sender']}: {'; '.join(x['why'])}" for x in ignored]
    out += ["", "_General guidance from public sources, not legal advice. Nothing left this computer._"]
    return "\n".join(out)


def _e(s: str) -> str:
    return html.escape(str(s))


CSS = """
:root{--paper:#f6f1e7;--ink:#2b2420;--muted:#76695c;--line:#ddd2c0;--card:#fffaf1;--mari:#d9822b;--mari-soft:#f6dcc0;
--warn:#b4442e;--warn-soft:#f6d9d1;--ok:#4f6b3a;--ok-soft:#e1e8d4;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--paper:#1a1614;--ink:#efe6da;--muted:#a89a8a;--line:#3a322c;
--card:#221d1a;--mari:#e9a05a;--mari-soft:#3d2b1b;--warn:#e8846e;--warn-soft:#3b211b;--ok:#a8c48e;--ok-soft:#24301c}}
:root[data-theme=dark]{--paper:#1a1614;--ink:#efe6da;--muted:#a89a8a;--line:#3a322c;--card:#221d1a;--mari:#e9a05a;
--mari-soft:#3d2b1b;--warn:#e8846e;--warn-soft:#3b211b;--ok:#a8c48e;--ok-soft:#24301c}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 Georgia,'Iowan Old Style',serif}
main{max-width:1040px;margin:0 auto;padding:40px 16px 80px}
h1{font-size:clamp(28px,5vw,44px);line-height:1.1;margin:0 0 8px;font-weight:600;letter-spacing:-.01em}
h2{font-size:20px;margin:44px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.lede{color:var(--muted);margin:0 0 24px;font-size:17px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.stat b{display:block;font-size:30px;font-family:var(--mono);font-weight:600}.stat span{color:var(--muted);font-size:14px}
.stat.hot b{color:var(--mari)}.stat.warn b{color:var(--warn)}
.row{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--mari);border-radius:10px;padding:16px 18px;margin:12px 0}
.row.urgent{border-left-color:var(--warn)}.row.closed{border-left-color:var(--line);opacity:.75}
.row.cancel{border-left-color:var(--ok)}
.top{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:baseline}
.act{font:600 12px var(--mono);letter-spacing:.06em;padding:3px 8px;border-radius:999px;background:var(--mari-soft);color:var(--ink)}
.urgent .act{background:var(--warn-soft)}.cancel .act{background:var(--ok-soft)}
.what{font-size:18px;font-weight:600}.ref{font-family:var(--mono);color:var(--muted);font-size:14px}
.status{font-size:14px;color:var(--muted)}.urgent .status{color:var(--warn);font-weight:600}
blockquote{margin:10px 0 6px;padding:8px 12px;border-left:2px solid var(--line);color:var(--ink);font-style:italic;background:transparent}
blockquote cite{display:block;font-style:normal;font-size:13px;color:var(--muted);margin-top:4px;font-family:var(--mono)}
.how{font-size:15px;margin:8px 0 0}.how small{display:block;color:var(--muted);margin-top:4px}
.ghost{font-size:14px;color:var(--warn);margin-top:6px}
ul.scams{padding-left:18px}ul.scams li{margin:8px 0}ul.scams code{font-family:var(--mono);font-size:13px;color:var(--muted)}
footer{margin-top:48px;color:var(--muted);font-size:14px;border-top:1px solid var(--line);padding-top:16px}
"""


def page(holdings: list[Holding], ignored: list[dict], est: Estate, n_emails: int, n_read: int, model: str = "gemma4:e4b") -> str:
    s = summary(holdings, ignored, est, n_emails, n_read)
    stat = lambda n, label, cls="": f'<div class="stat {cls}"><b>{n}</b><span>{_e(label)}</span></div>'
    rows = []
    for h in holdings:
        r = h.route
        cls = "closed" if h.status == "closed" else "urgent" if (h.status in ("matured_unclaimed", "at_risk", "inoperative")
                                                                  or r["action"] == "CLAIM (URGENT)") else \
            "cancel" if r["action"] in ("CANCEL", "TRANSFER") else ""
        ev = h.evidence[-1]
        ghost = ""
        if h.after_death and h.kind in ("subscription", "credit_card", "utility", "pension"):
            ghost = (f'<div class="ghost">Still active after {est.date_of_death}: emails on '
                     f'{_e(", ".join(h.after_death))}</div>')
        rows.append(f"""<div class="row {cls}"><div class="top"><span class="act">{_e(r['action'])}</span>
<span class="what">{_e(h.institution)} · {_e(KIND_WORDS.get(h.kind, h.kind))}</span>
<span class="ref">{_e('XXXX' + h.last4) if h.last4 else ''}</span>
<span class="status">{_e(STATUS_WORDS.get(h.status, h.status))} · {len(h.evidence)} email{'s' if len(h.evidence) != 1 else ''}, {h.first_seen} → {h.last_seen}</span></div>
<blockquote>“{_e(mask(ev['quote']))}”<cite>email of {ev['date']}</cite></blockquote>{ghost}
<p class="how"><b>{_e(r['who'][:1].upper() + r['who'][1:])}</b> {_e(r['how'])}<small>{_e(r['portal'])}</small></p></div>""")
    scams = "".join(f"<li>{_e(x['date'])} · “{_e(x['subject'])}”<br><code>{_e(x['sender'])}</code> — {_e('; '.join(x['why']))}</li>"
                    for x in ignored)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ghost Ledger · {_e(est.deceased)}</title><style>{CSS}</style></head><body><main>
<h1>What {_e(est.deceased)} left behind</h1>
<p class="lede">Read from {_e(est.pronoun)} mailbox by {_e(model)} on this computer, {date.today():%d %b %Y}. Every line below quotes the email it came from. Account numbers are masked.</p>
<div class="stats">{stat(s['holdings'], 'holdings found')}{stat(s['claims'], 'to claim', 'hot')}{stat(s['urgent'], 'need attention first', 'warn')}
{stat(s['still_charging'], 'still charging after death', 'warn')}{stat(s['scams'], 'scam emails ignored')}{stat(f"{s['read']}/{s['emails']}", 'emails read by the model')}</div>
<h2>What to do, in order</h2>{''.join(rows)}
<h2>Ignored: these looked like scams</h2><p class="lede">Families are targeted right after a death. These emails were never used as evidence.</p><ul class="scams">{scams or '<li>None.</li>'}</ul>
<footer>Ghost Ledger · general guidance from public sources (RBI, AMFI, IEPF, EPFO, insurers), not legal advice. The mailbox never left this computer.</footer>
</main></body></html>"""
