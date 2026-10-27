"""Auth0 for the executor: sign-in, Gmail through Token Vault, and phone approval (CIBA + Guardian push).

Why this matters for an estate: Ghost Ledger acts on someone's behalf with a grieving family's Gmail.
  - Ghost Ledger never sees or stores a Google password or Google token on disk. Auth0 Token Vault holds
    the Google tokens; we exchange our Auth0 refresh token for a short-lived Gmail token only when a letter
    is actually sent.
  - No letter goes out until the executor approves that exact letter on her phone (Guardian push). The
    approval request names the institution and the account ending, so she knows what she's approving.

Flows used:
  login            Authorization Code with a localhost callback, offline_access -> Auth0 refresh token.
  connect-gmail    Connected Accounts (My Account API) -> Google tokens stored in Token Vault.
  google_token     Refresh-token exchange with Token Vault -> Google access token (minutes).
  approve          CIBA /bc-authorize -> Guardian push -> poll /oauth/token.
"""
from __future__ import annotations

import json
import re
import secrets
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from . import config

GMAIL_SCOPES = ["openid", "profile", "email",
                "https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]
MY_ACCOUNT_SCOPES = "openid profile offline_access create:me:connected_accounts read:me:connected_accounts delete:me:connected_accounts"


class AuthError(RuntimeError):
    pass


def _base() -> str:
    if not config.auth0_ready():
        raise AuthError("Auth0 isn't configured. Put AUTH0_DOMAIN, AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET in .env")
    return f"https://{config.AUTH0_DOMAIN}"


def _redirect() -> str:
    return f"http://localhost:{config.CALLBACK_PORT}/callback"


def _store_path():
    config.SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    return config.SECRETS_DIR / "auth0.json"


def load() -> dict:
    p = _store_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save(d: dict) -> None:
    _store_path().write_text(json.dumps(d, indent=1), encoding="utf-8")


def _post(path: str, data: dict, token: str | None = None, as_json: bool = False) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if as_json:
        return requests.post(_base() + path, json=data, headers=headers, timeout=30)
    return requests.post(_base() + path, data=data, headers=headers, timeout=30)


def _check(r: requests.Response, what: str) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {"error": r.text[:300]}
    if r.status_code >= 400:
        raise AuthError(f"{what} failed ({r.status_code}): {body.get('error_description') or body.get('error') or body}")
    return body


# ------------------------------------------------------------------ browser round trip
def _browser_round_trip(url: str, want: str) -> dict:
    """Open url in the browser and wait for Auth0/Google to redirect back to our localhost callback."""
    got: dict = {}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if not self.path.startswith("/callback"):
                self.send_response(404)
                self.end_headers()
                return
            got.update({k: v[0] for k, v in q.items()})
            ok = want in got
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Done. You can close this tab and go back to the terminal." if ok else \
                f"Something went wrong: {got.get('error_description') or got.get('error') or 'no ' + want}"
            self.wfile.write(f"<html><body style='font:18px Georgia;padding:40px'><h2>Ghost Ledger</h2><p>{msg}</p></body></html>".encode())
            done.set()

        def log_message(self, *a):
            pass

    srv = HTTPServer(("localhost", config.CALLBACK_PORT), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    print(f"Opening your browser. If it doesn't open, visit:\n{url}\n")
    webbrowser.open(url)
    try:
        if not done.wait(timeout=300):
            raise AuthError("Timed out waiting for the browser (5 minutes).")
    finally:
        srv.shutdown()
    if want not in got:
        raise AuthError(f"Browser came back without {want}: {got.get('error_description') or got.get('error') or got}")
    return got


# ------------------------------------------------------------------ 1. executor sign-in
def login() -> dict:
    state = secrets.token_urlsafe(16)
    url = _base() + "/authorize?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": config.AUTH0_CLIENT_ID, "redirect_uri": _redirect(),
        "scope": "openid profile email offline_access", "state": state, "prompt": "login"})
    got = _browser_round_trip(url, "code")
    if got.get("state") != state:
        raise AuthError("State mismatch on login callback.")
    tok = _check(_post("/oauth/token", {"grant_type": "authorization_code", "client_id": config.AUTH0_CLIENT_ID,
                                        "client_secret": config.AUTH0_CLIENT_SECRET, "code": got["code"],
                                        "redirect_uri": _redirect()}), "Code exchange")
    if "refresh_token" not in tok:
        raise AuthError("No refresh token. In Auth0, turn on 'Refresh Token' grant for the app and keep offline_access.")
    claims = _jwt_claims(tok.get("id_token", ""))
    store = {"refresh_token": tok["refresh_token"], "sub": claims.get("sub"), "email": claims.get("email"),
             "name": claims.get("name")}
    save({**load(), **store})
    return store


def _jwt_claims(jwt: str) -> dict:
    import base64
    try:
        part = jwt.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    except Exception:
        return {}


def _refresh_token() -> str:
    rt = load().get("refresh_token")
    if not rt:
        raise AuthError("Not signed in. Run: python -m ghostledger login")
    return rt


# ------------------------------------------------------------------ 2. connect Gmail into Token Vault
def connect_gmail(connection: str = "google-oauth2") -> dict:
    me = _check(_post("/oauth/token", {"grant_type": "refresh_token", "client_id": config.AUTH0_CLIENT_ID,
                                       "client_secret": config.AUTH0_CLIENT_SECRET, "refresh_token": _refresh_token(),
                                       "audience": f"https://{config.AUTH0_DOMAIN}/me/", "scope": MY_ACCOUNT_SCOPES}),
                "My Account API token")["access_token"]
    state = secrets.token_urlsafe(16)
    start = _check(_post("/me/v1/connected-accounts/connect",
                         {"connection": connection, "redirect_uri": _redirect(), "state": state, "scopes": GMAIL_SCOPES},
                         token=me, as_json=True), "Connected Accounts connect")
    url = start["connect_uri"] + "?" + urllib.parse.urlencode({"ticket": start["connect_params"]["ticket"]})
    got = _browser_round_trip(url, "connect_code")
    done = _check(_post("/me/v1/connected-accounts/complete",
                        {"auth_session": start["auth_session"], "connect_code": got["connect_code"],
                         "redirect_uri": _redirect()}, token=me, as_json=True), "Connected Accounts complete")
    save({**load(), "connected_account": done.get("id"), "gmail_scopes": done.get("scopes")})
    return done


# ------------------------------------------------------------------ 3. Gmail token from Token Vault
def google_token(connection: str = "google-oauth2") -> str:
    body = _check(_post("/oauth/token", {
        "grant_type": "urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token",
        "client_id": config.AUTH0_CLIENT_ID, "client_secret": config.AUTH0_CLIENT_SECRET,
        "subject_token_type": "urn:ietf:params:oauth:token-type:refresh_token", "subject_token": _refresh_token(),
        "requested_token_type": "http://auth0.com/oauth/token-type/federated-connection-access-token",
        "connection": connection}), "Token Vault exchange")
    return body["access_token"]


# ------------------------------------------------------------------ 4. approval on the executor's phone
BINDING_OK = re.compile(r"[^A-Za-z0-9 +\-_.,:#]")


def binding_message(text: str) -> str:
    """Auth0 allows letters, digits, spaces and + - _ . , : # ; at most 64 characters."""
    return re.sub(r"\s+", " ", BINDING_OK.sub("", text)).strip()[:64]


def start_approval(text: str, expiry_s: int = 300) -> dict:
    sub = load().get("sub")
    if not sub:
        raise AuthError("Not signed in. Run: python -m ghostledger login")
    hint = json.dumps({"format": "iss_sub", "iss": f"https://{config.AUTH0_DOMAIN}/", "sub": sub})
    return _check(_post("/bc-authorize", {"client_id": config.AUTH0_CLIENT_ID, "client_secret": config.AUTH0_CLIENT_SECRET,
                                          "login_hint": hint, "scope": "openid", "binding_message": binding_message(text),
                                          "requested_expiry": str(expiry_s)}), "CIBA bc-authorize")


def poll_approval(auth_req_id: str) -> tuple[str, int]:
    """One poll. Returns ('approved'|'denied'|'expired'|'pending', seconds to wait before polling again)."""
    r = _post("/oauth/token", {"grant_type": "urn:openid:params:grant-type:ciba", "auth_req_id": auth_req_id,
                               "client_id": config.AUTH0_CLIENT_ID, "client_secret": config.AUTH0_CLIENT_SECRET})
    if r.status_code == 200:
        return "approved", 0
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    err = body.get("error", "")
    if err == "authorization_pending":
        return "pending", 5
    if err == "slow_down":
        m = re.search(r"(\d+)", body.get("error_description", ""))
        return "pending", max(6, int(m.group(1)) if m else 10)
    if err == "access_denied":
        return "denied", 0
    if err == "expired_token" or (err == "invalid_grant" and "expired" in body.get("error_description", "").lower()):
        return "expired", 0  # the push timed out on the phone; the workflow asks again later
    raise AuthError(f"CIBA poll failed ({r.status_code}): {body or r.text[:200]}")


def approve_blocking(text: str, expiry_s: int = 300, heartbeat=lambda *_: None) -> str:
    req = start_approval(text, expiry_s)
    deadline = time.time() + expiry_s + 10
    wait = int(req.get("interval", 5))
    while time.time() < deadline:
        time.sleep(wait)
        heartbeat(req["auth_req_id"])
        status, wait = poll_approval(req["auth_req_id"])
        if status != "pending":
            return status
    return "expired"
