"""Held-out test estate: the mailbox of a fictional woman, Leela Menon (1951-2026), Kochi.

Written after the first Gemma run on Raghavendra Rao's estate, and frozen BEFORE Gemma ever reads it,
so the rules added after that run can be checked on emails they were not tuned on. Different person,
city, institutions and wording: some statements are HTML tables, dates are written several ways, there
is a loan (a liability), an inoperative account, a deposit closed on maturity (trap), a fund house that
sends both a statement and a promotion, and different scams.

Everything is invented. Sender domains use the reserved `.example` TLD.
Writes data/estate2/mails/<id>.eml and data/estate2/truth.yaml.
"""
from __future__ import annotations

import email.utils
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "data" / "estate2"
OWNER = "Leela Menon <leela.menon51@mail.example>"
MAILS: list[dict] = []


def mail(mid, date, sender, subject, body, kind, refs=(), html=False):
    MAILS.append(dict(id=mid, date=date, sender=sender, subject=subject, body=body.strip("\n"),
                      kind=kind, refs=list(refs), html=html))


# ---------------------------------------------------------------- B1 Periyar Bank savings ...6127 (HTML statements)
for i, (d, bal) in enumerate([("2022-02-04", "1,88,210.00"), ("2024-08-03", "2,41,775.50"), ("2026-04-02", "2,96,430.15")]):
    mail(f"pyr-sb-{i}", d, "Periyar Bank <alerts@periyarbank.example>", f"e-Statement {d[:7]} | Periyar Bank",
         f"""
<html><body>
<p>Namaskaram Smt. LEELA MENON,</p>
<p>Your monthly statement is ready.</p>
<table border="1">
<tr><td>Account</td><td>Savings Bank - Senior Citizen</td></tr>
<tr><td>Account Number</td><td>XXXX XXXX 6127</td></tr>
<tr><td>Branch</td><td>Edappally, Kochi</td></tr>
<tr><td>Closing balance</td><td>&#8377; {bal}</td></tr>
</table>
<p>Periyar Bank Ltd. | This is an auto-generated message.</p>
</body></html>
""", "asset", ["B1"], html=True)

# ---------------------------------------------------------------- B2 pension, PPO credited into ...6127
for i, d in enumerate(["2025-06-30", "2026-04-30"]):
    nice = datetime.fromisoformat(d).strftime("%d/%m/%Y")
    mail(f"pyr-pen-{i}", d, "Periyar Bank <alerts@periyarbank.example>", "Credit alert: pension",
         f"""
Dear Customer, Rs. 31,206.00 has been credited to A/c no. XXXX6127 on {nice}.
Narration: KERALA STATE PENSION PPO KL/HS/1987/20934.
- Periyar Bank
""", "asset", ["B2"])

# ---------------------------------------------------------------- B3 Malabar Gramin Bank term deposit, matured, unclaimed
mail("mgb-td-0", "2020-03-02", "Malabar Gramin Bank <deposits@malabargramin.example>", "Term deposit opened",
     """
Dear Madam,
We confirm the opening of Term Deposit No. MGB-TD-558319 for Rs. 1,75,000 for 36 months at 6.9% p.a.
It will mature on 02 March 2023.
Malabar Gramin Bank, Aluva branch
""", "asset", ["B3"])
mail("mgb-td-1", "2025-01-15", "Malabar Gramin Bank <deposits@malabargramin.example>", "Unpaid maturity proceeds",
     """
Dear Smt. Leela Menon,
Term Deposit No. MGB-TD-558319 reached maturity on 02 March 2023. Since no renewal or closure request has been
received, the maturity proceeds of Rs. 2,15,940 are lying unpaid with the bank. Kindly visit the Aluva branch with
the deposit receipt and KYC documents.
Malabar Gramin Bank
""", "asset", ["B3"])

# ---------------------------------------------------------------- B4 Periyar Bank FD closed on maturity (trap)
mail("pyr-fd-0", "2021-11-09", "Periyar Bank <deposits@periyarbank.example>", "Fixed deposit renewed",
     "Your Fixed Deposit A/c 50214410 of Rs. 2,00,000 has been renewed for 12 months. Maturity: Nov 9, 2022.",
     "asset_closed", ["B4"])
mail("pyr-fd-1", "2022-11-10", "Periyar Bank <deposits@periyarbank.example>", "Fixed deposit closed",
     """
Dear Customer, your Fixed Deposit A/c 50214410 matured on Nov 9, 2022 and has been closed as per your standing
instruction. Proceeds of Rs. 2,14,260 have been credited to your savings account XXXX6127.
""", "asset_closed", ["B4"])

# ---------------------------------------------------------------- B5 Backwaters Life endowment policy
for i, d in enumerate(["2023-08-01", "2025-08-01"]):
    mail(f"bwl-{i}", d, "Backwaters Life <care@backwaterslife.example>", "Premium paid - thank you",
         f"""
Dear Leela Menon,
We have received your annual premium of Rs. 18,760 for policy BL-77120453 (Backwaters Golden Years Endowment).
Sum assured: Rs. 4,00,000. Policy term ends 2031. Nominee: Arjun Menon.
""", "asset", ["B5"])

# ---------------------------------------------------------------- B6 Arabian Sea Mutual Fund folio (statement from the AMC itself)
for i, d in enumerate(["2024-04-12", "2026-01-11"]):
    mail(f"asm-{i}", d, "Arabian Sea Mutual Fund <statements@arabiansea-mf.example>", "Account statement",
         f"""
<html><body>
<h3>Arabian Sea Mutual Fund - Account Statement</h3>
<p>Investor: LEELA MENON &nbsp; Folio: 8830291/04</p>
<table border="1"><tr><th>Scheme</th><th>Units</th><th>Value (Rs.)</th></tr>
<tr><td>Arabian Sea Conservative Hybrid Fund - Growth</td><td>3,401.112</td><td>1,02,377.80</td></tr></table>
<p>Nominee: Arjun Menon</p>
</body></html>
""", "asset", ["B6"], html=True)

# ---------------------------------------------------------------- B7 Nila Pharma physical shares, IEPF warning
mail("nila-0", "2025-06-18", "Nila Pharmaceuticals Ltd <secretarial@nilapharma.example>",
     "Notice: transfer of shares to IEPF",
     """
Dear Shareholder,
Registered Folio: NP00093561 (physical certificate, 150 equity shares)
Dividends for the last seven consecutive years have not been encashed. In accordance with the Companies Act, these
shares will be transferred to the Investor Education and Protection Fund Authority unless a valid claim is lodged
with our registrar by 30 September 2025.
""", "asset", ["B7"])

# ---------------------------------------------------------------- B8 Konkan Housing Finance home loan (liability)
for i, d in enumerate(["2025-10-05", "2026-04-05"]):
    mail(f"khf-{i}", d, "Konkan Housing Finance <service@konkanhf.example>", "EMI debited",
         f"""
Dear Customer, EMI of Rs. 12,480 for loan account KHF/HL/0047712 has been debited on {d}.
Principal outstanding: Rs. {'6,02,118' if i == 0 else '5,48,930'}. Loan cover: none on record.
""", "liability", ["B8"])

# ---------------------------------------------------------------- B9 Lotus credit card ending 3388
for i, (d, due) in enumerate([("2025-12-14", "6,210.00"), ("2026-06-14", "3,945.00")]):
    mail(f"lot-{i}", d, "Lotus Card Services <statements@lotuscards.example>", "Your Lotus card statement",
         f"""
Statement for Lotus Rewards credit card ending 3388.
Total amount due: Rs. {due}. Payment due by 03/{d[5:7]}/{d[:4]}.
Standing instructions on this card: MELODYBOX MUSIC.
""", "liability", ["B9"])

# ---------------------------------------------------------------- B10 PPF at the post office
mail("ppf-0", "2025-04-20", "Sabari Post Office <ppf@sabaripost.example>", "PPF annual balance",
     "Balance in your Public Provident Fund account no. 0310008842 as on 31.03.2025: Rs. 6,48,201.00. Account extended up to 2028.",
     "asset", ["B10"])

# ---------------------------------------------------------------- B11 demat with Malabar Capital
mail("mcap-0", "2025-09-08", "Malabar Capital <dp@malabarcapital.example>", "Holding statement",
     """
Demat holding statement - DP ID IN302910, Client ID 18832205 - LEELA MENON
COCHIN SHIPWORKS LTD   45 shares
SPICE COAST FOODS LTD  80 shares
Value as on 05-09-2025: Rs. 61,830.40
""", "asset", ["B11"])

# ---------------------------------------------------------------- B12 health insurance
mail("kch-0", "2025-11-20", "Kerala Care Health <renewals@keralacare.example>", "Policy renewed",
     "Your Kerala Care Senior Shield policy KCH/2025/551902 is renewed till 19-11-2026. Insured: Leela Menon. Sum insured Rs. 3,00,000.",
     "asset", ["B12"])

# ---------------------------------------------------------------- B13 inoperative savings at Kochi Co-operative Bank
mail("kcb-0", "2024-02-26", "Kochi Co-operative Bank <info@kochicoopbank.example>", "Your account is inoperative",
     """
Dear Member,
Savings account no. 0021455530 has had no customer-induced transactions for over two years and has been classified as
inoperative. Balance: Rs. 38,912.44. Please visit the Kaloor branch with KYC documents to reactivate it.
""", "asset", ["B13"])

# ---------------------------------------------------------------- subscriptions and a utility, some charging after death
for i, d in enumerate(["2026-03-02", "2026-06-02", "2026-08-02"]):
    mail(f"mel-{i}", d, "MelodyBox <billing@melodybox.example>", "Thanks for staying with MelodyBox",
         "Your MelodyBox Family plan has renewed. Rs. 179 was charged to your Lotus card ending 3388.", "subscription", ["T1"])
for i, d in enumerate(["2025-07-01", "2026-07-01"]):
    mail(f"chd-{i}", d, "Coastal Herald <subscriptions@coastalherald.example>", "Subscription renewed",
         "Your Coastal Herald digital edition (Subscriber No. CH-30815) has been renewed for 12 months at Rs. 990.",
         "subscription", ["T2"])
mail("fit-0", "2026-07-15", "FitLife Studio <hello@fitlife.example>", "Membership auto-renewed",
     "Hi Leela, your FitLife Silver membership (Member ID FL-2291) auto-renewed today for Rs. 1,500 per month.",
     "subscription", ["T3"])
for i, d in enumerate(["2026-02-10", "2026-08-10"]):
    mail(f"kwa-{i}", d, "Kochi Water Authority <bills@kochiwater.example>", "Water bill",
         f"Consumer No. KWA/EK/88210, Leela Menon, Edappally. Bill amount Rs. {'412' if i == 0 else '388'}. Due within 15 days.",
         "utility", ["U1"])

# ---------------------------------------------------------------- promotions (must not become holdings)
mail("pro-0", "2026-02-01", "Arabian Sea Mutual Fund <invest@arabiansea-mf.example>",
     "NFO: Arabian Sea Small Cap Opportunities Fund",
     "The new fund offer opens 10 Feb. Invest from Rs. 500. Existing investors can add a scheme to their folio online.",
     "promo")
mail("pro-1", "2026-03-18", "Konkan Housing Finance <offers@konkanhf.example>", "Pre-approved top-up loan of Rs. 5 lakh",
     "Valued customer, you are eligible for a top-up loan of Rs. 5,00,000 at 9.1%. No documents needed.", "promo")
mail("pro-2", "2026-05-02", "Lotus Card Services <offers@lotuscards.example>", "Upgrade to Lotus Platinum",
     "Get 5X rewards and lounge access. Upgrade your card in one click. Annual fee waived for the first year.", "promo")

# ---------------------------------------------------------------- scams
mail("scm-0", "2026-06-20", "Backwaters Life Claims <backwaters.claims.desk@freemail.example>",
     "Death claim of Rs. 4,00,000 ready - pay GST to release",
     """
Dear Arjun Menon, the death claim on your mother's policy is approved. Pay GST of Rs. 7,200 to the account below
within 24 hours to release the amount. Reply with your bank card details for verification.
""", "scam", ["B5"])
mail("scm-1", "2026-07-03", "SIM Services <kyc.sim.update@freemail.example>", "Your SIM will be deactivated",
     "Your mobile number will be deactivated today. Complete KYC immediately at http://sim-kyc-now.example", "scam")
mail("scm-2", "2026-06-11", "Pension Department <pension.verify@freemail.example>", "Pension stopped - life certificate pending",
     "Your pension will be blocked. Share OTP received on your phone to update life certificate.", "scam", ["B2"])
mail("scm-3", "2025-12-30", "Unclaimed Wealth Help <help@unclaimedwealth.example>",
     "Rs. 9.8 lakh unclaimed shares found in your name",
     "We traced shares worth Rs. 9,80,000 in your name. Our officer will recover them for a 12% service fee. Call our officer now.",
     "scam")

# ---------------------------------------------------------------- ordinary life (noise)
LIFE = [
    ("2026-05-12", "Arjun Menon <arjun.menon@mail.example>", "Doctor appointment Thursday",
     "Amma, I booked the appointment for Thursday 11 am. I will pick you up at 10."),
    ("2026-03-08", "Edappally Residents Association <era@kochiresidents.example>", "Women's day programme",
     "Dear residents, the programme starts at 5 pm in the community hall. Payasam will be served."),
    ("2026-01-26", "Retired Nurses Forum <rnf@kochinurses.example>", "Republic Day meet",
     "Members are invited for flag hoisting at 8 am followed by breakfast. Annual contribution Rs. 300."),
    ("2025-12-20", "Kochi Metro <tickets@kochimetro.example>", "Trip receipt",
     "Your trip from Edappally to MG Road. Fare Rs. 30 paid via card ending 3388."),
    ("2026-04-14", "Anjali Nair <anjali.n@mail.example>", "Vishu wishes",
     "Vishu ashamsakal Leela chechi! Sending some photos of the kani."),
    ("2026-05-02", "Kerala Ayurveda Store <orders@keralaayur.example>", "Order shipped",
     "Your order #KA-77810 (2 items) has been shipped."),
    ("2026-06-03", "Ravi Pillai <ravi.p@mail.example>", "Condolences",
     "Arjun, so sorry to hear about your mother. She took care of my father at the hospital for years."),
    ("2025-09-15", "Periyar Bank <otp@periyarbank.example>", "One time password",
     "Your OTP is 551208 for login. Periyar Bank never asks for your OTP."),
    ("2026-02-27", "Library Kochi <notices@kochilibrary.example>", "Book due",
     "'Randamoozham' is due for return on 6 March."),
    ("2026-04-28", "St. Mary's Church <office@stmarys.example>", "Feast committee",
     "Thank you for your contribution of Rs. 500 to the feast committee."),
]
for i, (d, s, subj, body) in enumerate(LIFE):
    mail(f"life-{i:02d}", d, s, subj, body, "personal")

TRUTH = {
    "person": "Leela Menon (1951-2026), retired nurse, Kochi. Fictional. HELD-OUT estate, frozen before any model run.",
    "executor": "Arjun Menon (son). Fictional.",
    "date_of_death": "2026-05-30",
    "items": {
        "B1": dict(kind="bank_account", institution="Periyar Bank", ident="6127", status="active"),
        "B2": dict(kind="pension", institution="Periyar Bank", ident="0934", alt=["6127"], status="active"),
        "B3": dict(kind="fixed_deposit", institution="Malabar Gramin Bank", ident="8319", status="matured_unclaimed"),
        "B4": dict(kind="fixed_deposit", institution="Periyar Bank", ident="4410", status="closed",
                   note="TRAP: closed on maturity in 2022, proceeds already paid."),
        "B5": dict(kind="life_insurance", institution="Backwaters Life", ident="0453", status="active"),
        "B6": dict(kind="mutual_fund", institution="Arabian Sea Mutual Fund", ident="0291", status="active"),
        "B7": dict(kind="shares_physical", institution="Nila Pharmaceuticals", ident="3561", status="at_risk_iepf"),
        "B8": dict(kind="loan", institution="Konkan Housing Finance", ident="7712", status="active",
                   note="Liability: inform the lender, check loan cover."),
        "B9": dict(kind="credit_card", institution="Lotus Card Services", ident="3388", status="active"),
        "B10": dict(kind="ppf", institution="Sabari Post Office", ident="8842", status="active"),
        "B11": dict(kind="demat", institution="Malabar Capital", ident="2910", alt=["2205"], status="active"),
        "B12": dict(kind="health_insurance", institution="Kerala Care Health", ident="1902", status="active"),
        "B13": dict(kind="bank_account", institution="Kochi Co-operative Bank", ident="5530", status="inoperative"),
        "T1": dict(kind="subscription", institution="MelodyBox", ident="", alt=["3388"], status="active"),
        "T2": dict(kind="subscription", institution="Coastal Herald", ident="0815", status="active"),
        "T3": dict(kind="subscription", institution="FitLife Studio", ident="2291", status="active"),
        "U1": dict(kind="utility", institution="Kochi Water Authority", ident="8210", status="active"),
    },
    "traps": {
        "closed": ["B4"],
        "scam_emails": [m["id"] for m in MAILS if m["kind"] == "scam"],
        "promo_emails": [m["id"] for m in MAILS if m["kind"] == "promo"],
    },
    "emails": {m["id"]: {"kind": m["kind"], "refs": m["refs"]} for m in MAILS},
}


def main():
    out = ROOT / "mails"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.eml"):
        old.unlink()
    for m in MAILS:
        msg = EmailMessage()
        msg["From"] = m["sender"]
        msg["To"] = OWNER
        msg["Subject"] = m["subject"]
        msg["Date"] = email.utils.format_datetime(datetime.fromisoformat(m["date"] + "T10:15:00+05:30"))
        msg["Message-ID"] = f"<{m['id']}@estate2.example>"
        if m["html"]:
            msg.set_content(m["body"] + "\n", subtype="html")
        else:
            msg.set_content(m["body"] + "\n")
        (out / f"{m['id']}.eml").write_bytes(bytes(msg))
    (ROOT / "truth.yaml").write_text(yaml.safe_dump(TRUTH, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (ROOT / "estate.yaml").write_text(yaml.safe_dump({
        "deceased": "Leela Menon", "date_of_death": "2026-05-30", "executor": "Arjun Menon", "relation": "son",
        "executor_email": "arjun.menon@mail.example", "city": "Kochi", "pronoun": "her"}, sort_keys=False), encoding="utf-8")
    kinds: dict[str, int] = {}
    for m in MAILS:
        kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    print(f"{len(MAILS)} emails -> {out}", kinds)


if __name__ == "__main__":
    main()
