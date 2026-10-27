"""What the family does next for each kind of holding: who to contact, which official route, what papers.

This is general guidance gathered from public sources (RBI, AMFI, IEPF, EPFO, insurers' published
claim procedures). It is not legal advice. Requirements differ by institution and by amount; where
there is no nominee, larger amounts usually need a succession certificate or legal heir certificate.
"""
from __future__ import annotations

COMMON_DOCS = ["Death certificate (several attested copies)", "Claimant's KYC (PAN, Aadhaar or other ID, address proof)",
               "Proof of being the nominee, or legal heir documents if there is no nominee", "Cancelled cheque of the claimant's bank account"]

ROUTES: dict[str, dict] = {
    "bank_account": dict(action="CLAIM", who="the bank's home branch",
                         how="Submit the bank's deceased-depositor claim form. Nominees get a simpler process.",
                         portal="If the account has been inactive for 10+ years, search UDGAM (udgam.rbi.org.in) for deposits moved to RBI's DEA Fund."),
    "fixed_deposit": dict(action="CLAIM", who="the issuing bank's branch",
                          how="Claim the deposit (and any matured amount) with the original receipt or a lost-receipt indemnity.",
                          portal="Matured deposits left unclaimed for 10 years move to RBI's DEA Fund; UDGAM (udgam.rbi.org.in) searches them."),
    "ppf": dict(action="CLAIM", who="the bank or post office holding the PPF account",
                how="A PPF cannot continue after death; the nominee claims the balance with the death certificate and passbook. Without a nominee, legal heirs use Form G (more documents above Rs 1 lakh).", portal=""),
    "gold_bond": dict(action="CLAIM", who="the bank or depository through which the Sovereign Gold Bond is held",
                      how="Request transmission to the nominee or legal heir; it can then be held to maturity or redeemed early on an interest date.", portal=""),
    "pension": dict(action="STOP + FAMILY PENSION", who="the pension-disbursing bank and the pension sanctioning office",
                    how="Report the death so pension stops (credits after death are recovered). The spouse can apply for family pension with the PPO number.", portal=""),
    "mutual_fund": dict(action="CLAIM", who="the fund house or its registrar (the CAS shows which), or MF Central",
                        how="Submit a transmission request for each folio. With no nominee, current SEBI rules let heirs claim up to Rs 10 lakh with an indemnity, affidavits and proof of relationship (notarised above Rs 5 lakh); above that, a succession certificate or probated will. Confirm with the fund house.",
                        portal="mfcentral.com accepts transmission requests online for many fund houses."),
    "demat": dict(action="CLAIM", who="the depository participant (broker/bank) that runs the demat account",
                  how="Submit the Transmission Request Form; shares move to the claimant's own demat account. Simplified documents are accepted up to a value limit if there is no nominee; ask the DP for the current limit.", portal=""),
    "shares_physical": dict(action="CLAIM (URGENT)", who="the company's registrar and transfer agent",
                            how="Claim transmission and the unpaid dividends now. Shares whose dividends go unclaimed for 7 years are transferred to IEPF.",
                            portal="If already transferred, file Form IEPF-5 online at iepf.gov.in."),
    "life_insurance": dict(action="CLAIM", who="the insurer's claims department",
                           how="File a death claim for in-force policies; for matured-but-unpaid policies, claim the maturity amount too.",
                           portal="Insurers must let you search unclaimed amounts on their websites; Bima Bharosa handles grievances."),
    "health_insurance": dict(action="INFORM", who="the health insurer",
                             how="Report the death; remove the member and keep cover running for the surviving family. Claim any pending hospital bills.", portal=""),
    "provident_fund": dict(action="CLAIM", who="EPFO, through the last employer or the EPFO portal",
                           how="Form 20 (PF balance), Form 10D (pension) and Form 5(IF) (EDLI insurance) for nominees or legal heirs.", portal=""),
    "credit_card": dict(action="INFORM + CLOSE", who="the card issuer",
                        how="Report the death and close the card. Dues are settled from the estate, not by heirs personally. Stop the auto-debits listed below first.", portal=""),
    "loan": dict(action="INFORM", who="the lender",
                 how="Report the death; check for loan insurance before anything is paid from the estate.", portal=""),
    "subscription": dict(action="CANCEL", who="the service", how="Cancel the plan so the card stops being charged.", portal=""),
    "utility": dict(action="TRANSFER", who="the utility office", how="Transfer the connection to the surviving occupant's name.", portal=""),
    "other": dict(action="CHECK", who="the institution named in the evidence", how="Ask what is held and how to claim it.", portal=""),
}

NOTHING_TO_DO = dict(action="NOTHING (closed)", who="", how="The evidence shows this was closed while he was alive.", portal="")


def route_for(kind: str, status: str) -> dict:
    if status == "closed":
        return NOTHING_TO_DO
    return ROUTES.get(kind, ROUTES["other"])
