"""Build the synthetic test estate: the mailbox of a fictional man, Raghavendra Rao (1958-2026).

Everything here is invented: the person, his family, every bank, insurer, fund and company, and
every number. Sender domains use the reserved `.example` TLD so no real organisation is imitated.
Only the *kinds* of documents are real: Indian bank statements, FD renewal notices, insurance
premium reminders, consolidated account statements, EPF passbook updates, dividend notices.

The point is a mailbox where we know the full truth, so the eval can say exactly what was found,
what was missed, and what was invented. Writes:
  data/estate/mails/<id>.eml      one file per email
  data/estate/truth.yaml          every asset, liability and subscription, and every trap
"""
from __future__ import annotations

import email.utils
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "data" / "estate"
OWNER = "Raghavendra Rao <raghu.rao1958@mail.example>"

MAILS: list[dict] = []


def mail(mid, date, sender, subject, body, kind, refs=(), html=False):
    MAILS.append(dict(id=mid, date=date, sender=sender, subject=subject, body=body.strip("\n"),
                      kind=kind, refs=list(refs), html=html))


# ---------------------------------------------------------------- A1 Kaveri Bank savings ...4821
for i, (d, bal) in enumerate([("2019-04-03", "2,14,382.40"), ("2021-10-02", "3,02,110.75"),
                              ("2023-07-04", "4,48,906.10"), ("2025-01-03", "5,12,774.00"),
                              ("2026-05-03", "5,61,209.35"), ("2026-08-02", "5,74,018.90")]):
    mail(f"kav-sb-{i}", d, "Kaveri Bank e-Statements <estatements@kaveribank.example>",
         f"Your Kaveri Bank Savings Account statement - {d[:7]}",
         f"""
Dear RAGHAVENDRA RAO,

Your e-statement for Savings Account No. XXXXXXX4821 for the period ending {d} is attached.

Account Summary
Account Type      : Kaveri Senior Citizen Savings
Branch            : Saraswathipuram, Mysuru
Closing Balance   : Rs. {bal}
Nominee Registered: Yes

The attachment is password protected. Password is first four letters of your name in capitals
followed by your date of birth in DDMM format.

This is a system generated mail. Please do not reply.
Kaveri Bank Ltd.

[Attachment: Statement_XXXX4821_{d[:7]}.pdf]
""", "asset", ["A1"])

# ---------------------------------------------------------------- A14 pension credit into ...4821
for i, d in enumerate(["2024-03-01", "2025-11-01", "2026-07-31"]):
    mail(f"kav-pen-{i}", d, "Kaveri Bank Alerts <alerts@kaveribank.example>",
         "Pension credited to your account",
         f"""
Dear Customer,
Your A/c XXXXXXX4821 is credited with Rs. 38,450.00 on {d} towards PENSION - STATE GOVT (PPO No. KA/EDU/58/11604).
Available balance: please check net banking.
If this credit was not expected, call 1800-000-0000.
- Kaveri Bank
""", "asset", ["A14"])

# ---------------------------------------------------------------- A15 SGB held with Kaveri Bank
for i, d in enumerate(["2023-02-10", "2025-08-11"]):
    mail(f"kav-sgb-{i}", d, "Kaveri Bank Alerts <alerts@kaveribank.example>",
         "Sovereign Gold Bond - semi-annual interest credited",
         f"""
Dear RAGHAVENDRA RAO,
Semi-annual interest of Rs. 1,725.00 on your Sovereign Gold Bond holding (SGB 2020-21 Series VI,
30 grams, Holding ID SGB0000462731) has been credited to A/c XXXXXXX4821 on {d}.
The bond matures in 2028. Premature redemption is allowed on interest payment dates after the fifth year.
Regards,
Government Business Department, Kaveri Bank
""", "asset", ["A15"])

# ---------------------------------------------------------------- A12 PPF with Kaveri Bank
for i, d in enumerate(["2022-04-05", "2025-04-04"]):
    mail(f"kav-ppf-{i}", d, "Kaveri Bank e-Statements <estatements@kaveribank.example>",
         "Annual statement - Public Provident Fund account",
         f"""
Dear RAGHAVENDRA RAO,

Please find the annual statement for your PPF Account No. XXXXXX0912 for FY {int(d[:4])-1}-{d[2:4]}.

Opening balance : Rs. {'7,82,450.00' if i == 0 else '11,06,318.00'}
Deposits        : Rs. 1,50,000.00
Interest (7.1%) : Rs. {'61,210.00' if i == 0 else '83,940.00'}
Closing balance : Rs. {'9,93,660.00' if i == 0 else '13,40,258.00'}
Account extended for a block of 5 years from 2021.

Kaveri Bank Ltd. - Saraswathipuram Branch
""", "asset", ["A12"])

# ---------------------------------------------------------------- A13 Kaveri credit card ...9012 (liability)
for i, (d, due) in enumerate([("2024-12-08", "12,406.00"), ("2026-06-08", "8,915.50"), ("2026-08-08", "4,388.00")]):
    mail(f"kav-cc-{i}", d, "Kaveri Bank Cards <cardstatements@kaveribank.example>",
         "Kaveri Platinum Credit Card statement",
         f"""
Dear Cardholder,
Your statement for Kaveri Platinum Credit Card ending 9012 is ready.
Total Amount Due : Rs. {due}
Minimum Due      : Rs. {round(float(due.replace(',', '')) * 0.05, 2):,.2f}
Payment Due Date : {d[:8]}28
Recurring charges on this card include STREAMBOX PREMIUM and AIRWAVE POSTPAID.
Kaveri Bank Card Services
""", "liability", ["A13"])

# ---------------------------------------------------------------- A2 Malnad Co-op FD ...7703, matured, unclaimed
mail("mal-fd-0", "2019-06-14", "Malnad Co-operative Bank <fd.services@malnadbank.example>",
     "Renewal advice - Fixed Deposit",
     """
Dear Sri Raghavendra Rao,
Your Fixed Deposit Receipt No. MCB/FD/00417703 of Rs. 3,00,000.00 has been auto-renewed on 14-06-2019
for a period of 60 months at 7.25% p.a. Maturity date: 14-06-2024. Maturity value: Rs. 4,29,812.00.
Nominee: Smt. Vasantha Rao.
Kindly preserve this advice. Malnad Co-operative Bank Ltd., Ramakrishnanagar Branch.
""", "asset", ["A2"])
mail("mal-fd-1", "2024-07-20", "Malnad Co-operative Bank <fd.services@malnadbank.example>",
     "Your deposit has matured - action needed",
     """
Dear Sri Raghavendra Rao,
Your Fixed Deposit Receipt No. MCB/FD/00417703 matured on 14-06-2024. As no renewal or payment
instructions were received, the maturity amount of Rs. 4,29,812.00 is held as matured unclaimed deposit
and earns savings bank interest only. Please visit the branch with the original receipt and KYC to claim it.
Deposits remaining unclaimed for 10 years are transferred to the Depositor Education and Awareness Fund.
Malnad Co-operative Bank Ltd.
""", "asset", ["A2"])

# ---------------------------------------------------------------- A3 Coastal Bank savings ...2210, CLOSED (trap)
mail("cst-sb-0", "2020-03-02", "Coastal Bank <statements@coastalbank.example>",
     "Coastal Bank account statement Feb 2020",
     """
Dear Customer, the statement for your savings account ending 2210 for February 2020 is attached.
Closing balance: Rs. 18,240.55. - Coastal Bank
[Attachment: CBS_2210_Feb2020.pdf]
""", "asset_closed", ["A3"])
mail("cst-sb-1", "2021-09-17", "Coastal Bank <service@coastalbank.example>",
     "Account closure confirmation",
     """
Dear Raghavendra Rao,
As per your request dated 10-09-2021, your savings account ending 2210 has been closed and the balance of
Rs. 18,902.10 has been transferred to your Kaveri Bank account. We are sorry to see you go.
Coastal Bank
""", "asset_closed", ["A3"])

# ---------------------------------------------------------------- A4 Nilgiri Life policy ...4471 (active)
for i, d in enumerate(["2021-01-05", "2023-01-04", "2025-01-06", "2026-01-05"]):
    mail(f"nil-a-{i}", d, "Nilgiri Life Insurance <premium@nilgirilife.example>",
         "Premium due reminder",
         f"""
Dear Policyholder RAGHAVENDRA RAO,
Premium of Rs. 24,318.00 for your policy no. 812444471 (Nilgiri Jeevan Suraksha - Endowment, Sum Assured
Rs. 5,00,000) is due on {d[:4]}-01-28. Pay online at the customer portal or at any branch.
Nominee as per records: Ananya Rao (daughter).
Nilgiri Life Insurance Co. Ltd.
""", "asset", ["A4"])
mail("nil-a-r", "2026-01-29", "Nilgiri Life Insurance <receipts@nilgirilife.example>",
     "Premium receipt", """
Received with thanks Rs. 24,318.00 towards policy no. 812444471 for the premium due 28-01-2026.
Next due date: 28-01-2027. Nilgiri Life Insurance Co. Ltd.
""", "asset", ["A4"])

# ---------------------------------------------------------------- A5 Nilgiri Life policy ...3958 matured, unpaid
mail("nil-b-0", "2022-03-10", "Nilgiri Life Insurance <claims@nilgirilife.example>",
     "Maturity claim intimation - policy 806213958",
     """
Dear RAGHAVENDRA RAO,
Your policy no. 806213958 (Nilgiri Money Back 20) has matured on 15-04-2022. The maturity value payable is
Rs. 1,86,400.00. To receive the payment, please submit the discharge form, a cancelled cheque and KYC at
your servicing branch or through the customer portal.
Claims Department, Nilgiri Life Insurance Co. Ltd.
""", "asset", ["A5"])
mail("nil-b-1", "2023-05-02", "Nilgiri Life Insurance <claims@nilgirilife.example>",
     "Reminder: maturity amount awaiting your claim",
     """
Dear RAGHAVENDRA RAO,
Our records show that the maturity amount for policy no. 806213958 is still unpaid as the discharge
requirements have not been received. Unclaimed amounts are transferred to the Senior Citizens' Welfare
Fund after 10 years. Please submit the requirements at the earliest.
Nilgiri Life Insurance Co. Ltd.
""", "asset", ["A5"])

# ---------------------------------------------------------------- A6 Sahyadri health policy ...8820
for i, d in enumerate(["2025-02-20", "2026-02-18"]):
    mail(f"sah-{i}", d, "Sahyadri Health Insurance <renewals@sahyadrihealth.example>",
         "Your health policy has been renewed",
         f"""
Dear Raghavendra Rao,
Your Sahyadri Senior Care policy SHI/2024/00718820 has been renewed till {int(d[:4])+1}-02-19.
Insured members: Raghavendra Rao, Vasantha Rao. Sum insured Rs. 5,00,000. Premium paid Rs. 41,226.
Sahyadri Health Insurance Ltd.
""", "asset", ["A6"])

# ---------------------------------------------------------------- A7, A8 mutual funds via CAS
for i, (d, v1, v2) in enumerate([("2022-01-12", "2,10,442.18", "96,310.40"), ("2023-07-11", "2,61,903.77", "1,14,286.05"),
                                 ("2025-01-13", "3,38,512.60", "1,42,770.31"), ("2026-07-10", "3,71,034.92", "1,58,118.47")]):
    mail(f"cas-{i}", d, "Consolidated Investor Services <cas@cisregistry.example>",
         f"Consolidated Account Statement for {d[:7]}",
         f"""
CONSOLIDATED ACCOUNT STATEMENT
Name: RAGHAVENDRA RAO   PAN: XXXXX1234X   Email: raghu.rao1958@mail.example

Folio No: 10293341 / 72      Tungabhadra Mutual Fund
  Tungabhadra Balanced Advantage Fund - Regular Growth
  Closing units: 4,812.330   Market value: Rs. {v1}
  Nominee: Ananya Rao

Folio No: 5527098            Western Ghats Mutual Fund
  Western Ghats Nifty 50 Index Fund - Direct Growth
  Closing units: 612.044     Market value: Rs. {v2}
  Nominee: Not registered

This statement is issued by Consolidated Investor Services on behalf of the fund houses.
""", "asset", ["A7", "A8"])

# ---------------------------------------------------------------- A9 demat with Bharat Securities
for i, d in enumerate(["2023-03-09", "2025-03-10", "2026-08-09"]):
    mail(f"dmt-{i}", d, "National Depository CAS <cas@ndepository.example>",
         "Your Consolidated Account Statement (demat)",
         f"""
NDS CAS for the month ending {d[:7]}
Demat account: Bharat Securities Ltd. - DP ID IN301926 Client ID XXXX6650
Holdings:
  DECCAN CEMENTS LTD        INE00DC01017    120 shares    Value Rs. {'31,440.00' if i < 2 else '38,760.00'}
  HAMPI TEXTILES LTD        INE00HT01022     40 shares    Value Rs. {'5,212.00' if i < 2 else '4,980.00'}
Total portfolio value: Rs. {'36,652.00' if i < 2 else '43,740.00'}
""", "asset", ["A9"])
mail("dmt-div-0", "2025-08-21", "Deccan Cements Ltd - Registrar <dividend@deccancements.example>",
     "Dividend credited - Deccan Cements Ltd",
     """
Dear Shareholder,
Final dividend of Rs. 7.50 per share for FY 2024-25 has been credited for 120 shares held in your demat
account with Bharat Securities Ltd. (DP ID IN301926, Client ID XXXX6650). Net amount Rs. 900.00 credited to the bank account registered with your depository participant.
""", "asset", ["A9"])

# ---------------------------------------------------------------- A10 Hampi Textiles unclaimed dividend (IEPF risk)
mail("hmp-0", "2024-11-05", "Hampi Textiles Ltd <investors@hampitextiles.example>",
     "Unclaimed dividend - shares liable to be transferred to IEPF",
     """
Dear Shareholder (Folio No. HT0042117),
Our records show that dividends declared for FY 2017-18 to FY 2023-24 on your physical shareholding of 200
shares under Folio No. HT0042117 have remained unclaimed. Under the Companies Act, shares on which dividend is
unclaimed for seven consecutive years will be transferred to the Investor Education and Protection Fund (IEPF).
Please claim the dividend before 28-02-2025 by writing to our Registrar with a request letter and KYC.
Company Secretary, Hampi Textiles Ltd.
""", "asset", ["A10"])

# ---------------------------------------------------------------- A11 EPF from his first job, old UAN
for i, d in enumerate(["2017-09-30", "2019-12-02"]):
    mail(f"epf-{i}", d, "EPF Passbook <passbook@epfo-updates.example>",
         "EPF passbook updated",
         f"""
Dear Member,
Your EPF passbook for UAN XXXXXXXX1187 (Member ID KN/BNG/0054321/000/0001122, establishment: Mysore Sugar Allied
Industries) has been updated. Balance as on {d}: Rs. {'1,84,200' if i == 0 else '2,02,915'}.
No contribution received since 2016. Inoperative accounts continue to earn interest till age 58.
""", "asset", ["A11"])

# ---------------------------------------------------------------- subscriptions and utilities (ghost charges)
for i, d in enumerate(["2025-12-01", "2026-07-01", "2026-09-01"]):
    mail(f"sbx-{i}", d, "StreamBox <billing@streambox.example>", "Your StreamBox Premium renewal",
         f"""
Hi Raghavendra, your StreamBox Premium plan renewed on {d} for Rs. 499.00, charged to your card ending 9012.
Next renewal: {int(d[:4]) + (d[5:7] == '12')}-{int(d[5:7]) % 12 + 1:02d}-01. Manage or cancel any time in Account > Membership.
""", "subscription", ["S1"])
for i, d in enumerate(["2026-04-06", "2026-08-06"]):
    mail(f"air-{i}", d, "Airwave Telecom <ebill@airwave.example>", "Airwave postpaid bill",
         f"""
Dear Customer, your Airwave postpaid bill for mobile number XXXXXX3021 is Rs. 449.00, due {d[:8]}20.
Auto-pay is active on card ending 9012.
""", "subscription", ["S2"])
for i, d in enumerate(["2025-10-12", "2026-10-12"]):
    mail(f"mdy-{i}", d, "The Mysuru Daily <subscriptions@mysurudaily.example>", "E-paper subscription renewed",
         """
Thank you for renewing your annual e-paper subscription (Rs. 1,200.00). Subscriber ID MD-77812.
""", "subscription", ["S3"])
mail("chs-0", "2026-03-15", "ChessMasters Pro <no-reply@chessmasters.example>", "Annual plan renewed",
     "Your ChessMasters Pro annual plan (Rs. 2,999.00) renewed today. Keep climbing that rating!", "subscription", ["S4"])
for i, d in enumerate(["2026-06-11", "2026-09-10"]):
    mail(f"pwr-{i}", d, "Mysuru Power Supply <bills@mysurupower.example>", "Electricity bill",
         f"""
Bill for RR No. SPM-44817 (Raghavendra Rao, #1182, 4th Cross, Saraswathipuram): Rs. {'1,214' if i == 0 else '1,086'}.00 due {d[:8]}25.
""", "utility", ["U1"])

# ---------------------------------------------------------------- promotions (real senders, NOT holdings)
mail("pro-0", "2026-05-14", "Kaveri Bank Offers <offers@kaveribank.example>",
     "Pre-approved personal loan of Rs. 8,00,000 for you",
     "Dear Customer, you are pre-approved for a personal loan up to Rs. 8,00,000 at 10.49%. Apply in 2 minutes on net banking.",
     "promo")
mail("pro-1", "2026-02-02", "Tungabhadra Mutual Fund <updates@tungabhadramf.example>",
     "NFO: Tungabhadra Defence Opportunities Fund opens 10 Feb",
     "Invest from Rs. 500. The New Fund Offer of Tungabhadra Defence Opportunities Fund opens 10 Feb and closes 24 Feb. Read the scheme documents carefully.",
     "promo")
mail("pro-2", "2025-09-19", "CoverWise Compare <quotes@coverwise.example>",
     "Your term insurance quote: Rs. 1 crore cover",
     "Hi Raghavendra, based on your enquiry, here is a quote for Rs. 1 crore term cover at Rs. 2,840/month. This is a quote, not a policy.",
     "promo")
mail("pro-3", "2026-06-30", "Bharat Securities Research <research@bharatsec.example>",
     "Weekly market outlook: cement stocks to watch",
     "Our analysts like DECCAN CEMENTS and two other cement names this quarter. This is research, not advice.",
     "promo")

# ---------------------------------------------------------------- scams (look like assets, must be ignored)
mail("scm-0", "2026-07-18", "Kaveri Bank KYC Team <kaveribank.kyc.update@freemail.example>",
     "URGENT: Your Kaveri Bank account will be BLOCKED today",
     """
Dear Customer, your account XXXXXXX4821 KYC has expired. Your account will be blocked within 24 hours.
Update PAN immediately at http://kaveri-kyc-verify.example/login to avoid suspension.
""", "scam", ["A1"])
mail("scm-1", "2026-03-03", "Nilgiri Life Bonus Dept <nilgiri.bonus.claims@freemail.example>",
     "Bonus of Rs. 3,45,000 approved on your policy",
     """
Congratulations! A loyalty bonus of Rs. 3,45,000 has been approved on your Nilgiri Life policy. Pay a refundable
processing fee of Rs. 4,999 to the account below to release the bonus within 48 hours.
""", "scam")
mail("scm-2", "2026-08-12", "Income Tax Refund <refund-itd@taxrefund-gov.example>",
     "Income tax refund of Rs. 18,450 approved",
     "You are eligible for a refund of Rs. 18,450. Submit your bank card details at http://itr-refund-now.example within 24 hours.",
     "scam")
mail("scm-3", "2026-09-02", "Electricity Board <alert.power@freemail.example>",
     "Power will be disconnected tonight at 9:30 pm",
     "Your previous month bill was not updated. Call our officer on 90000 00000 immediately to avoid disconnection.",
     "scam")
mail("scm-4", "2025-12-24", "Western Ghats MF Unclaimed Cell <wgmf.unclaimed@freemail.example>",
     "Unclaimed mutual fund units of Rs. 6,20,000 in your name",
     """
We found unclaimed units worth Rs. 6,20,000 in folio 99018273 in your name. Our agent will help you claim them for a
15% service fee. Reply with your Aadhaar and bank details.
""", "scam")
mail("scm-5", "2026-04-01", "Lucky Draw India <winner@luckydraw.example>", "You have WON Rs. 25 lakh",
     "Your email was selected in the international lucky draw. Send Rs. 12,500 for processing.", "scam")

# ---------------------------------------------------------------- ordinary life (noise)
LIFE = [
    ("2026-08-15", "Ananya Rao <ananya.rao@mail.example>", "Photos from Mysuru Dasara rehearsal",
     "Appa, sharing the photos from yesterday. Aditya loved the elephants! Will call on Sunday."),
    ("2026-06-02", "Ananya Rao <ananya.rao@mail.example>", "Re: your BP medicines",
     "I have ordered your monthly medicines on the pharmacy app, it will reach by Thursday."),
    ("2026-01-14", "Retired Teachers' Forum <forum@rtfmysuru.example>", "Sankranti get-together on 18th",
     "Dear members, our Sankranti get-together is on 18th at the Town Hall annexe, 4 pm. Contribution Rs. 200."),
    ("2025-11-20", "Sri Chamundeshwari Temple Trust <seva@templetrust.example>", "Seva receipt",
     "Received Rs. 1,001.00 towards Annadana seva. Receipt No. 55120. May the Goddess bless your family."),
    ("2026-04-22", "RailYatra Bookings <tickets@railyatra.example>", "Booking confirmed: Mysuru to Chennai",
     "PNR 4419027713. Mysuru Jn to Chennai Central, 3A, 2 passengers. Fare Rs. 2,310.00 paid by UPI."),
    ("2026-05-30", "ShopKart <orders@shopkart.example>", "Your order has been delivered",
     "Your order of Reading glasses (2 pairs) worth Rs. 1,198 has been delivered."),
    ("2026-07-07", "Kaveri Bank <otp@kaveribank.example>", "OTP for net banking login",
     "Your OTP for net banking login is 482913. Do not share it with anyone. Kaveri Bank will never ask for your OTP."),
    ("2026-03-28", "Vasantha Rao <vasantha.r@mail.example>", "Shopping list",
     "Please get coriander, 1 kg tomato and the mysore pak for Ananya's visit."),
    ("2025-12-10", "Old Colleagues Group <group@mysuruteachers.example>", "Fwd: Funny video",
     "Forwarded as received. Watch till the end!"),
    ("2026-02-21", "Ananya Rao <ananya.rao@mail.example>", "Sent you money for the AC repair",
     "Appa I sent Rs. 6,000 to your account on UPI for the AC repair, please confirm once you get it."),
    ("2026-08-25", "Mysuru Pharmacy <orders@mysurupharmacy.example>", "Order dispatched",
     "Your order #MP-20918 (3 items) has been dispatched."),
    ("2025-07-03", "Library Notices <notices@mysurulibrary.example>", "Book due reminder",
     "The book 'Malgudi Days' is due for return on 10 July."),
    ("2026-09-14", "Ravi Kumar <ravi.k@mail.example>", "Condolences",
     "Ananya, deeply sorry to hear about your father. He taught me mathematics for three years. Om Shanti."),
    ("2024-10-02", "Gandhi Jayanti Committee <info@gjcommittee.example>", "Thank you volunteers",
     "Thank you for volunteering at the cleanliness drive. Certificates will be mailed."),
    ("2025-06-18", "DocVault <noreply@docvault.example>", "Document issued",
     "Your driving licence has been issued to your document wallet."),
]
for i, (d, s, subj, body) in enumerate(LIFE):
    mail(f"life-{i:02d}", d, s, subj, body, "personal")

# ---------------------------------------------------------------- write
TRUTH = {
    "person": "Raghavendra Rao (1958-2026), retired school teacher, Mysuru. Fictional.",
    "executor": "Ananya Rao (daughter). Fictional.",
    "date_of_death": "2026-06-21",
    "items": {
        "A1": dict(kind="bank_account", institution="Kaveri Bank", ident="4821", status="active",
                   note="Savings account; pension and SGB interest are credited here."),
        "A2": dict(kind="fixed_deposit", institution="Malnad Co-operative Bank", ident="7703", status="matured_unclaimed",
                   note="Forgotten FD: only two emails in seven years."),
        "A3": dict(kind="bank_account", institution="Coastal Bank", ident="2210", status="closed",
                   note="TRAP: closed in 2021. Must not be listed as something to claim."),
        "A4": dict(kind="life_insurance", institution="Nilgiri Life Insurance", ident="4471", status="active"),
        "A5": dict(kind="life_insurance", institution="Nilgiri Life Insurance", ident="3958", status="matured_unclaimed",
                   note="Matured in 2022, never paid out."),
        "A6": dict(kind="health_insurance", institution="Sahyadri Health Insurance", ident="8820", status="active",
                   note="No payout on death; inform insurer, keep spouse covered."),
        "A7": dict(kind="mutual_fund", institution="Tungabhadra Mutual Fund", ident="3341", status="active"),
        "A8": dict(kind="mutual_fund", institution="Western Ghats Mutual Fund", ident="7098", status="active",
                   note="No nominee: claim needs legal-heir documents."),
        "A9": dict(kind="demat", institution="Bharat Securities", ident="6650", status="active"),
        "A10": dict(kind="shares_physical", institution="Hampi Textiles", ident="2117", status="at_risk_iepf",
                    note="Physical shares, unclaimed dividends, may already be with IEPF."),
        "A11": dict(kind="provident_fund", institution="EPFO", ident="1187", status="inoperative"),
        "A12": dict(kind="ppf", institution="Kaveri Bank", ident="0912", status="active"),
        "A13": dict(kind="credit_card", institution="Kaveri Bank", ident="9012", status="active",
                    note="Liability: inform the bank, stop auto-debits."),
        "A14": dict(kind="pension", institution="Kaveri Bank", ident="1604", status="active",
                    note="Stop the pension; spouse may apply for family pension."),
        "A15": dict(kind="gold_bond", institution="Kaveri Bank", ident="2731", status="active"),
        "S1": dict(kind="subscription", institution="StreamBox", ident="", status="active"),
        "S2": dict(kind="subscription", institution="Airwave Telecom", ident="3021", status="active"),
        "S3": dict(kind="subscription", institution="The Mysuru Daily", ident="7812", status="active"),
        "S4": dict(kind="subscription", institution="ChessMasters Pro", ident="", status="active"),
        "U1": dict(kind="utility", institution="Mysuru Power Supply", ident="4817", status="active"),
    },
    "traps": {
        "closed": ["A3"],
        "scam_emails": [m["id"] for m in MAILS if m["kind"] == "scam"],
        "promo_emails": [m["id"] for m in MAILS if m["kind"] == "promo"],
    },
    "emails": {m["id"]: dict(kind=m["kind"], refs=m["refs"]) for m in MAILS},
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
        msg["Date"] = email.utils.format_datetime(datetime.fromisoformat(m["date"] + "T09:30:00+05:30"))
        msg["Message-ID"] = f"<{m['id']}@estate.example>"
        msg.set_content(m["body"] + "\n")
        (out / f"{m['id']}.eml").write_bytes(bytes(msg))
    (ROOT / "truth.yaml").write_text(yaml.safe_dump(TRUTH, sort_keys=False, allow_unicode=True), encoding="utf-8")
    kinds = {}
    for m in MAILS:
        kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    print(f"{len(MAILS)} emails -> {out}", kinds)


if __name__ == "__main__":
    main()
