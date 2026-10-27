"""Write the inheritance map, report pages and draft letters to an output folder."""
from __future__ import annotations

import json
from pathlib import Path

from . import ledger, letters, report
from .schema import reading_to_dict


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
