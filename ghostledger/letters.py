"""Claim and intimation letters, filled from a fixed template. No model writes these.

A letter to a bank is a legal-ish document. It must say exactly what the evidence says and nothing
more, so it is assembled from the holding's verified fields. Gemma's job ends at finding the holding.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .ledger import Holding
from .routes import COMMON_DOCS

KIND_WORDS = {
    "bank_account": "savings/current account", "fixed_deposit": "fixed deposit", "ppf": "PPF account",
    "gold_bond": "Sovereign Gold Bond holding", "pension": "pension account (PPO)", "mutual_fund": "mutual fund folio",
    "demat": "demat account", "shares_physical": "physical shareholding", "life_insurance": "life insurance policy",
    "health_insurance": "health insurance policy", "provident_fund": "provident fund account (UAN)",
    "credit_card": "credit card", "loan": "loan account", "subscription": "subscription", "utility": "connection",
}

ASK = {
    "CLAIM": "I request you to share the claim / transmission procedure and the list of documents required, and to "
             "confirm the balance or amount payable as on the date of death.",
    "CLAIM (URGENT)": "Please record this intimation immediately and do not transfer these holdings or the unpaid "
                      "dividends to the Investor Education and Protection Fund while the transmission is in process. "
                      "Kindly share the transmission procedure and the documents required.",
    "STOP + FAMILY PENSION": "Please stop further pension credits from the date of death and share the procedure for "
                             "the spouse's family pension.",
    "INFORM + CLOSE": "Please block the card, stop all recurring charges on it, close the account and share the final "
                      "statement. Any dues will be settled from the estate.",
    "INFORM": "Please record the death against this account and advise the next steps.",
    "CANCEL": "Please cancel this plan with effect from the date of death and stop all further charges.",
    "TRANSFER": "Please advise the procedure to transfer this connection to the surviving occupant.",
    "CHECK": "Please let me know what is held in his name and how it can be claimed.",
}


@dataclass
class Estate:
    deceased: str
    date_of_death: str
    executor: str
    relation: str
    executor_email: str
    executor_phone: str = ""
    city: str = ""
    pronoun: str = "his"  # the deceased's: "I am his daughter"

    @classmethod
    def from_dict(cls, d: dict) -> "Estate":
        return cls(**{k: str(v) for k, v in d.items() if k in cls.__dataclass_fields__})


def subject(h: Holding, est: Estate) -> str:
    ref = f" ending {h.last4}" if h.last4 else ""
    verb = "Claim intimation" if h.route["action"].startswith("CLAIM") else "Intimation of death"
    return f"{verb}: {KIND_WORDS.get(h.kind, h.kind)}{ref} of late {est.deceased}"


def body(h: Holding, est: Estate, today: date | None = None, follow_up: int = 0) -> str:
    today = today or date.today()
    action = h.route["action"]
    what = KIND_WORDS.get(h.kind, h.kind)
    ref = f" ending {h.last4}" if h.last4 else ""
    lines = [
        "To,", f"{h.institution}", "",
        f"Date: {today:%d-%m-%Y}", "",
        f"Subject: {subject(h, est)}" + (f" (reminder {follow_up})" if follow_up else ""), "",
        "Dear Sir / Madam,", "",
    ]
    if follow_up:
        lines += [f"This is reminder {follow_up} to my earlier letter about the {what}{ref}. I have not yet received "
                  "a response or an acknowledgement number.", ""]
    lines += [
        f"I write to inform you that {est.deceased}, who held the {what}{ref} with you, passed away on "
        f"{est.date_of_death}. I am {est.pronoun} {est.relation} and the executor of {est.pronoun} estate.", "",
        ASK.get(action, ASK["CHECK"]), "",
    ]
    if action.startswith("CLAIM") or action.startswith("STOP"):
        lines += ["I can provide the following on request:"] + [f"  - {d}" for d in COMMON_DOCS] + [""]
    lines += ["Please reply to this email with an acknowledgement or reference number.", "",
              "Yours faithfully,", est.executor, f"{est.relation.capitalize()} of late {est.deceased}", est.executor_email]
    if est.executor_phone:
        lines.append(est.executor_phone)
    return "\n".join(lines)


def needs_letter(h: Holding) -> bool:
    return h.status != "closed" and h.route["action"] not in ("NOTHING (closed)",)


# Where to go when an institution doesn't answer. Banks, deposits, PPF, pension and cards: RBI's Integrated
# Ombudsman (after 30 days without a reply). Insurance: Bima Bharosa / Insurance Ombudsman. Funds, demat and
# listed shares: SEBI SCORES. EPF: EPFiGMS.
REGULATOR = {
    **dict.fromkeys(["bank_account", "fixed_deposit", "ppf", "gold_bond", "pension", "credit_card", "loan"],
                    ("RBI Integrated Ombudsman", "https://cms.rbi.org.in")),
    **dict.fromkeys(["life_insurance", "health_insurance"], ("IRDAI Bima Bharosa", "https://bimabharosa.irdai.gov.in")),
    **dict.fromkeys(["mutual_fund", "demat", "shares_physical"], ("SEBI SCORES", "https://scores.sebi.gov.in")),
    "provident_fund": ("EPFO grievance portal (EPFiGMS)", "https://epfigms.gov.in"),
}


def escalation(h: Holding, est: Estate, sent_on: list[str], today: date | None = None) -> dict:
    who, portal = REGULATOR.get(h.kind, ("the institution's grievance officer", ""))
    what = KIND_WORDS.get(h.kind, h.kind)
    ref = f" ending {h.last4}" if h.last4 else ""
    dates = ", ".join(sent_on)
    body = "\n".join([
        f"Complaint to: {who}" + (f" ({portal})" if portal else ""),
        f"Against: {h.institution}", f"Date: {(today or date.today()):%d-%m-%Y}", "",
        f"Subject: No response to death claim intimation for the {what}{ref} of late {est.deceased}", "",
        f"{est.deceased} passed away on {est.date_of_death}. As {est.pronoun} {est.relation} and executor I wrote to "
        f"{h.institution} on {dates} asking for the claim procedure for the {what}{ref}. I have received no reply "
        "or acknowledgement number.", "",
        "I request your office to direct the institution to acknowledge the claim and share the procedure.", "",
        "Copies of the letters sent are attached.", "", est.executor, est.executor_email])
    return {"to_portal": portal, "regulator": who,
            "subject": f"Complaint: no response from {h.institution} on {what}{ref}", "body": body}
