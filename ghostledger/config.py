"""Settings from environment variables, with an optional .env file next to where you run the command."""
from __future__ import annotations

import os
from pathlib import Path


def load_env(path: str | Path = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()


def get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


AUTH0_DOMAIN = get("AUTH0_DOMAIN").replace("https://", "").rstrip("/")
AUTH0_CLIENT_ID = get("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = get("AUTH0_CLIENT_SECRET")
CALLBACK_PORT = int(get("GHOST_CALLBACK_PORT", "8765"))
SECRETS_DIR = Path(get("GHOST_SECRETS", ".secrets"))
TEMPORAL_ADDRESS = get("TEMPORAL_ADDRESS", "localhost:7233")
TASK_QUEUE = get("GHOST_TASK_QUEUE", "ghost-ledger")
# One "day" in the claim workflow. 86400 for real use; the demo compresses 15 days into a few minutes.
DAY_SECONDS = int(get("GHOST_DAY_SECONDS", "86400"))
# Where letters really go. Institutions in the demo estate are fictional, so the demo sends every letter
# to an inbox you control (plus-addressing keeps them apart: you+malnad-bank@gmail.com).
DEMO_TO = get("GHOST_DEMO_TO")
APPROVER = get("GHOST_APPROVER", "guardian")  # guardian (Auth0 CIBA push) or console (CLI signal)
SENDER = get("GHOST_SENDER", "gmail")  # gmail (Auth0 Token Vault) or outbox (write .eml files)


def auth0_ready() -> bool:
    return bool(AUTH0_DOMAIN and AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET)
