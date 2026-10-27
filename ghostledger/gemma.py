"""Gemma (through Ollama, on the family's own machine) reads one email.

Per email:
  1. Gemma lists what the email says the owner holds, owes or pays for, each with the exact sentence.
  2. grounding.check verifies every item against the email.
  3. Rejected items get ONE retry that names the problem. Anything still unsupported is dropped
     and recorded, never guessed.
Answers are cached by (model, prompt version, email) so re-running a report or the eval is free and
the same email always gives the same answer.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import requests

from . import grounding, scam
from .schema import KINDS, OLLAMA_SCHEMA, STATUSES, Email, Item, Reading

PROMPT_VERSION = "v1"
DEFAULT_MODEL = os.environ.get("GHOST_MODEL", "gemma4:e4b")
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL
MAX_CHARS = 9000

SYSTEM_PROMPT = f"""You help a family find what a person who has died left behind. You read ONE email from
their mailbox and list the financial things it shows they held, owed or paid for. You copy facts; you never
guess, infer or fill gaps.

Return JSON with:
- about_holding: true only if the email is from an institution about a specific account, deposit, policy,
  folio, demat account, shareholding, provident fund, pension, card, loan, subscription or utility connection
  that this person holds. false for promotions, offers, quotes, research, newsletters, OTPs, personal mail.
- looks_like_scam: true if the email pressures for fees, card or identity details, threatens to block an
  account, promises prizes, or claims to be an institution while writing from a personal address.
- items: one entry per distinct holding the email shows (a statement can show several folios). For each:
  - kind: one of {", ".join(KINDS)}
  - institution: the bank, insurer, fund house, company or service, as written.
  - identifier: the account / policy / folio / receipt / client / UAN / holding / subscriber number as written
    (masked forms like XXXX4821 are fine). null if the email gives none. Never make one up.
  - status: one of {", ".join(STATUSES)}. "closed" only if the email says it was closed. "matured_unclaimed"
    only if it says it matured AND the money is unclaimed/unpaid. "at_risk" if it warns of transfer to IEPF
    or a similar fund. "inoperative" if it says no contributions/transactions for a long time.
  - evidence: the shortest sentence or line from the email that shows this holding, copied word for word.
If the email is not about a holding, or looks like a scam, return items: [].
A promotion that names a fund or a loan is NOT a holding. An offer is NOT a policy."""

RETRY_PROMPT = """Some items are not supported by the email:
{problems}
Read the email again. For each listed item, either fix it so the evidence is copied word for word and the
identifier really appears in the email, or remove the item. Keep the other items exactly as before."""


class OllamaError(RuntimeError):
    pass


def _cache_path(cache: Path, model: str, e: Email) -> Path:
    key = hashlib.sha256(f"{model}|{PROMPT_VERSION}|{e.date}|{e.full_text}".encode()).hexdigest()[:24]
    return cache / f"{key}.json"


def _chat(messages: list[dict], model: str) -> dict:
    payload: dict[str, Any] = {
        "model": model, "messages": messages, "stream": False, "format": OLLAMA_SCHEMA, "think": False,
        "options": {"temperature": 0, "seed": 7, "num_ctx": 8192},
    }
    for attempt in range(2):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=900)
        except requests.ConnectionError as ex:
            raise OllamaError(f"Can't reach Ollama at {OLLAMA_URL}. Start it with `ollama serve`.") from ex
        if r.status_code == 400 and "think" in payload:
            payload.pop("think")  # older Ollama / models without a thinking switch
            continue
        if r.status_code != 200:
            raise OllamaError(f"Ollama {r.status_code}: {r.text[:300]}")
        return r.json()
    raise OllamaError("Ollama rejected the request")


def _items(data: dict) -> list[Item]:
    out = []
    for raw in (data.get("items") or [])[:4]:
        kind = raw.get("kind") if raw.get("kind") in KINDS else "other"
        status = raw.get("status") if raw.get("status") in STATUSES else "unknown"
        ident = raw.get("identifier")
        out.append(Item(kind=kind, institution=str(raw.get("institution") or "").strip(),
                        identifier=str(ident).strip() if ident not in (None, "", "null") else None,
                        status=status, evidence=str(raw.get("evidence") or "").strip()))
    return out


def _ground(items: list[Item], e: Email) -> list[Item]:
    for it in items:
        why = grounding.check(it, e)
        it.ok, it.reason = why is None, why or ""
        if it.ok:
            it.status = grounding.settle_status(it)
    return items


def read(e: Email, model: str = DEFAULT_MODEL, cache_dir: str | Path = ".cache/gemma", use_cache: bool = True) -> Reading:
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    cpath = _cache_path(cache, model, e)
    cached = json.loads(cpath.read_text(encoding="utf-8")) if use_cache and cpath.exists() else None
    responses: list[str] = cached["responses"] if cached else []
    timings: list[dict] = cached["timings"] if cached else []
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Email date: {e.date}\nFrom: {e.sender}\nSubject: {e.subject}\n\n{e.body[:MAX_CHARS]}"}]

    def call(i: int) -> dict:
        if i < len(responses):
            return json.loads(responses[i])
        t0 = time.perf_counter()
        resp = _chat(messages, model)
        content = resp.get("message", {}).get("content", "{}")
        responses.append(content)
        timings.append({"ms": round((time.perf_counter() - t0) * 1000), "out_tokens": resp.get("eval_count")})
        return json.loads(content)

    first = call(0)
    items = _ground(_items(first), e)
    rejected = [f"{it.kind} {it.institution} ({it.identifier}): {it.reason}" for it in items if not it.ok]
    retried = False
    if rejected:
        retried = True
        bad = [it for it in items if not it.ok]
        problems = "\n".join(f'- {it.kind} "{it.institution}" ({it.identifier}): {it.reason}' for it in bad)
        messages += [{"role": "assistant", "content": responses[0]},
                     {"role": "user", "content": RETRY_PROMPT.format(problems=problems)}]
        second = _ground(_items(call(1)), e)
        rejected += [f"retry: {it.kind} {it.institution} ({it.identifier}): {it.reason}" for it in second if not it.ok]
        items = [it for it in items if it.ok]
        seen = {(it.kind, it.last4) for it in items}
        items += [it for it in second if it.ok and (it.kind, it.last4) not in seen]
    items = [it for it in items if it.ok]  # anything unsupported is dropped, never guessed

    cpath.write_text(json.dumps({"model": model, "prompt_version": PROMPT_VERSION, "email_id": e.id,
                                 "responses": responses, "timings": timings}, indent=1), encoding="utf-8")
    return Reading(
        email_id=e.id,
        about_holding=bool(first.get("about_holding")),
        model_says_scam=bool(first.get("looks_like_scam")),
        scam_reasons=scam.check(e),
        items=items,
        meta={"retried": retried, "ms": sum(t["ms"] for t in timings[: 2 if retried else 1]),
              "rejected": rejected},
    )


def doctor(model: str = DEFAULT_MODEL) -> str:
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
    except Exception:
        return f"✗ Ollama is not running at {OLLAMA_URL}. Start the Ollama app or run `ollama serve`."
    names = [m["name"] for m in tags.get("models", [])]
    if not any(n == model or n.startswith(model.split(":")[0] + ":") for n in names):
        return f"✗ Ollama is running but {model} isn't pulled. Run: ollama pull {model}"
    return f"✓ Ollama is running and {model} is available."
