# Setting up Ghost Ledger

You can run the scan and the eval with only Ollama. Temporal, Auth0 and Gmail are needed only for the claim workflows.

## 0. Ollama + Gemma (required)

```
ollama pull gemma4:e4b
pip install -r requirements.txt
python -m ghostledger doctor
python -m ghostledger scan data/estate/mails       # writes out/report.html, out/ledger.json, out/letters/
python -m ghostledger eval                         # Gemma vs the regex baseline on the synthetic estate
```

## 1. Temporal (durable scan and claims)

Windows: `winget install Temporal.TemporalCLI`. macOS: `brew install temporal`. Linux: download it from temporal.download.

```
temporal server start-dev --db-filename temporal.db     # window 1. Web UI: http://localhost:8233
python -m ghostledger worker                            # window 2. Leave it running.
python -m ghostledger start-scan data/estate/mails      # window 3
```

You can stop the worker at any point, even in the middle of reading. When you start it again, the scan continues from the next unread email.

To try the claims without any accounts, set `GHOST_APPROVER=console`, `GHOST_SENDER=outbox` and `GHOST_DAY_SECONDS=20` in `.env`:

```
python -m ghostledger claim 1 2 3
python -m ghostledger board --watch
python -m ghostledger approve claim-malnad-co-operative-bank-fixed-deposit-7703 yes
```

## 2. Google Cloud (lets Auth0 hold Gmail access)

1. Go to console.cloud.google.com and create a project called "Ghost Ledger".
2. Open **APIs & Services → Library → Gmail API** and click **Enable**.
3. Open **Google Auth Platform** (OAuth consent screen) and choose **External**. Fill in the app name and your email.
   - **Audience → Test users:** add the Gmail address you will use.
   - **Data access → Add scopes:** `.../auth/gmail.send` and `.../auth/gmail.readonly`.
   - **Branding → Authorized domains:** `auth0.com`.
4. Open **Clients → Create client → Web application**.
   - Authorized redirect URI: `https://YOUR_AUTH0_DOMAIN/login/callback`
   - Copy the Client ID and Client secret.

## 3. Auth0 (sign-in, Token Vault, approvals on your phone)

1. Sign up at auth0.com. A new tenant includes Auth0 for AI Agents. Note the tenant domain, e.g. `dev-abc123.us.auth0.com`.
2. **Applications → Create Application → "Ghost Ledger" → Regular Web Application.**
   - **Settings → Allowed Callback URLs:** `http://localhost:8765/callback`
   - **Settings → Refresh Token Rotation:** turn it off. Token Vault does not support rotation.
   - **Advanced Settings → Grant Types:** Authorization Code, Refresh Token, Token Vault, Client Initiated Backchannel Authentication (CIBA). Save.
3. **Authentication → Social → Google.**
   - Paste the Google Client ID and secret.
   - Tick **Offline Access**.
   - Set the purpose to **Authentication and Connected Accounts for Token Vault**.
   - **Applications tab:** enable Ghost Ledger.
4. **Applications → APIs → Auth0 My Account API → Activate.**
   - **Application Access → Ghost Ledger → User Access: Authorized.**
   - Scopes: `create:me:connected_accounts`, `read:me:connected_accounts`, `delete:me:connected_accounts`.
5. **Ghost Ledger app → Multi-Resource Refresh Token:** enable **My Account API**.
   - **Settings → Access Settings:** turn on **Allow Skipping User Consent**.
6. **Security → Multi-factor Auth:**
   - Turn on **Push Notification using Auth0 Guardian**.
   - Set the policy to **Always** for now.
   - Install the **Auth0 Guardian** app on your phone.
7. **Ghost Ledger app → CIBA section:** set the notification channel to **Guardian Push**.
8. Copy `.env.example` to `.env` and fill in `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET` and `GHOST_DEMO_TO`.

Then run:

```
python -m ghostledger login            # sign in with Google; scan the Guardian QR code when asked
```

After you have enrolled, set the MFA policy back to **Never**, because Token Vault refuses token exchange while MFA is Always. Guardian approvals keep working, because CIBA uses the enrolled device.

```
python -m ghostledger connect-gmail    # consent to Gmail send/read once; Auth0 Token Vault stores it
python -m ghostledger test-approval    # your phone should buzz
```

## Why the demo sends to your own inbox

The banks and insurers in the synthetic estate are fictional (`.example` domains). Every letter goes to `GHOST_DEMO_TO` with a plus-tag for each institution (for example, `you+malnadcooperative@gmail.com`). To play the bank, reply from another address. The claim workflow sees the reply in the thread and closes the claim.
