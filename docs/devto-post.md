---
title: When someone dies, their money doesn't tell the family where it is. So a local Gemma reads their inbox.
published: false
tags: devchallenge, hf26challenge, ai, opensource
cover_image: https://raw.githubusercontent.com/samarthkumble/ghost-ledger/main/docs/img/cover.png
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26).*

## What I Built

India has **₹2.2 lakh crore** sitting unclaimed: ₹97,545 crore in bank deposits, ₹89,004 crore in shares and dividends, ₹20,062 crore in insurance, ₹10,915 crore in provident fund. Those are December 2025 figures from a 1 Finance report, [as reported by Business Today](https://www.businesstoday.in/personal-finance/news/story/rs-22-lakh-crore-unclaimed-funds-lie-idle-across-banks-epf-insurance-stocks-mfs-524958-2026-04-10). Among the causes it lists are *unreported deaths* and *heirs who don't know about legacy investments*.

That second cause is the ghost this project is about. Nobody keeps a list of what they own. An FD renewal notice arrives once every five years. A premium receipt arrives once a year. A dividend notice comes from a company someone bought shares in before the internet. When that person dies, the only complete map of their money is their inbox, and the family usually doesn't know how to read it.

**Ghost Ledger** reads it for them, on their own laptop:

1. **Gemma 4 (E4B, through Ollama) reads the mailbox** and writes an inheritance map. Every deposit, policy, folio, demat account, pension, loan and subscription goes on it, with the exact sentence from the email that proves it and the official route to claim it (UDGAM for old bank deposits, IEPF-5 for shares, AMC transmission for mutual funds, EPFO Form 20, and so on).
2. **Plain code checks every line Gemma writes.** If the quote isn't in the email, or the account number isn't in it, the line is dropped. It never guesses.
3. **For each claim the family chooses, a Temporal workflow takes over.** It drafts the letter, **asks the executor's phone for approval (Auth0 Guardian)**, sends it **from her own Gmail through Auth0 Token Vault**, waits 15 days on a durable timer, sends reminders, and finally drafts the complaint to the regulator.

Here's who I tested it on. **Raghavendra Rao** was a retired school teacher in Mysuru who died in June 2026. He is fictional; I wrote his 75-email mailbox by hand, with a written answer key, so the results could be scored. Here is what Ghost Ledger found in it:

- A **₹4,29,812 fixed deposit** at Malnad Co-operative Bank. It matured in 2024 and was never collected. There were only two emails about it in seven years.
- A **life policy that matured in 2022 and was never paid out**.
- **200 physical shares** of Hampi Textiles with seven years of unclaimed dividends. They are about to be moved to IEPF.
- A **state pension still being credited** after his death. The family has to stop it, because the bank will recover it otherwise.
- **A streaming plan, a postpaid phone bill and an e-paper subscription** still renewing, months after he died.

And here is what it refused to use:

- **Six scam emails**, including *"Pay a refundable processing fee of Rs. 4,999 to the account below to release the bonus"* and *"URGENT: Your Kaveri Bank account will be BLOCKED today"*.
- **A savings account he closed in 2021.**
- **Promotions** that name funds he never held.

## Demo

**Live site:** [ghostledger.tech](https://ghostledger.tech)
**The report Gemma produced for Raghavendra:** [ghostledger.tech/demo/report.html](https://ghostledger.tech/demo/report.html)

{% embed VIDEO_URL %}

![The inheritance map Ghost Ledger writes. Every line quotes the email it came from, and account numbers are masked.](https://raw.githubusercontent.com/samarthkumble/ghost-ledger/main/docs/img/report.png)

![A claim waiting on my phone: Auth0 Guardian asks before any letter leaves the executor's Gmail.](PHONE_SCREENSHOT)

![The claim letter, and the "bank's" reply, in Gmail.](GMAIL_SCREENSHOT)

![The same claim as a Temporal workflow: approval, send, and the durable 15-day wait.](TEMPORAL_SCREENSHOT)

## Code

{% github samarthkumble/ghost-ledger %}

## How I Built It

### 1. The reader: Gemma 4 on a laptop CPU

My laptop has a Ryzen 5 5500U and no GPU. Gemma 4 E4B runs there through Ollama at about **20 seconds per email**. A real mailbox holds ten years of mail, so Gemma only reads what could matter:

- **A cheap filter keeps emails that mention accounts or money.** It drops the shopping orders, temple receipts and "photos from Dasara". 51 of Raghavendra's 75 emails survive.
- **Scam checks run in code before the model sees anything.** These are free-mail senders claiming to be banks, fee requests, links to other domains, and "call our officer". A grieving family is exactly who these emails target, so they are never sent to Gemma and never become evidence.
- **Gemma answers in a fixed JSON schema** (Ollama's `format`, temperature 0). For each holding it gives the kind, institution, account number and the sentence that shows it.

Then comes the part that made this trustworthy enough to send letters from. Each item Gemma writes is checked by plain code:

```python
def check(item, email):
    if not in_email(item.evidence, email):
        return "the evidence is not copied word for word from the email"
    if not institution_named(item.institution, email):
        return f'"{item.institution}" is not named in the email'
    if item.kind not in ("subscription", "utility"):
        if not item.identifier:
            return "no account, policy, folio or other identifier: a mention is not a holding"
        if item.last4 not in digits(email):
            return f'the identifier "{item.identifier}" does not appear in the email'
```

A rejected item gets **one retry that names the problem**. If it still fails, it's dropped and logged. A promotion that says "invest in Western Ghats Mutual Fund" has no folio number, so it never becomes a holding.

Gemma's job ends at finding holdings. The claim letters are **fixed templates** filled from verified fields, because a letter to a bank should say exactly what the evidence says and nothing more.

### 2. Measured twice, and the second time on a mailbox it had never seen

Both mailboxes are invented, each with a written answer key. The regex baseline gets the same filters and the same checks, so the only difference is who reads the email.

| | Raghavendra (75 emails) | | Leela (47 emails, **held out**) | |
|---|---|---|---|---|
| | regex | Gemma | regex | Gemma |
| Holdings and debts found | 11 / 15 | **15 / 15** | 7 / 13 | **13 / 13** |
| Subscriptions and bills found | 3 / 5 | **5 / 5** | 1 / 4 | **4 / 4** |
| Matured / at-risk / dormant / closed caught | 4 / 5 | **5 / 5** | 2 / 4 | **4 / 4** |
| Invented entries | 0 | 0 | 1 | **1** |
| Filed as the wrong kind | 3 | 0 | 4 | 0 |
| Closed account put on the claim list | 0 | 0 | 0 | 0 |
| Scam emails used as evidence | 0 | 0 | 0 | 0 |

That table hides two things I'd rather tell you myself.

**Gemma's first run on Raghavendra was not clean.** It found all 15 holdings, but there was one invented entry, one wrong kind and one missed "matured" flag. When I read Gemma's raw answers, all three came from *my* code, not from Gemma:

- **The missed flag:** Gemma had correctly said "matured, unclaimed". My status check only read the one sentence Gemma quoted ("matured on 14-06-2024."), so it downgraded the status. The "held as matured unclaimed deposit" part was in the next sentence.
- **The invented entry:** Gemma called demat shares "physical shares", so my scorer couldn't match them to the demat account.
- **The wrong kind:** a card used to pay a phone bill became a separate "credit card at the phone company".

I fixed all three in code, with no prompt changes. A perfect score after fixing things on the same data proves very little, though. So I wrote a **second estate**: Leela Menon, a retired nurse in Kochi, with different banks, HTML statements, a home loan, a dormant account, a deposit already closed on maturity, and different scams. [I committed it and its answer key](https://github.com/samarthkumble/ghost-ledger/commit/d31d2ac) *before* any model read it, then ran it once.

**The held-out run first scored "0 invented", and that was wrong.** Gemma had turned a Kochi Metro trip receipt (paid by card) into a utility bill. My ledger then silently merged it into the *Kochi Water Authority* bill, because I compared only the first word of institution names. My scorer had the same shortcut, so it hid the error. I fixed both, and the honest number became **1**. I didn't add a rule for metro receipts, because that would be tuning on the held-out set.

### 3. Temporal: because a claim takes months

Settling an estate isn't a request and a response. You write to a bank, and they answer in three weeks, or never. That wait is the whole job, and it can't live in a cron job or a browser tab.

- **`EstateScan`** reads the mailbox as one durable activity per email. Close the laptop lid halfway and it continues from the next unread email. Gemma's answers are cached, so a retried read costs nothing.
- **`ClaimFlow`** runs one workflow per holding: draft → approval on the phone → send → wait → reminder → wait → reminder → complaint.

```python
for day in range(1, days + 1):
    self.state = f"waiting for a reply: day {day} of {days}"
    try:
        await workflow.wait_condition(lambda: self.reply is not None,
                                      timeout=timedelta(seconds=args["day_seconds"]))
    except asyncio.TimeoutError:
        pass
    found = await workflow.execute_activity(check_replies, ReplyArgs(thread_id, our_ids), ...)
    if found:
        return True
```

After two unanswered reminders, it drafts the complaint for the right regulator: RBI's Integrated Ombudsman for banks, Bima Bharosa for insurance, SEBI SCORES for funds and shares, EPFiGMS for provident fund. In demo mode a "day" is 20 seconds, so a 15-day wait takes 5 minutes. **I killed the worker in the middle of a wait. When I restarted it, the claim carried on from day 7, with nothing lost.**

### 4. Auth0 for AI Agents: acting with a grieving family's Gmail

This is the part I was most careful with. An agent that sends letters from someone's Gmail, on behalf of a dead parent, has to earn that.

- **The executor signs in with Auth0.** Her Gmail is connected once through Connected Accounts into **Token Vault**. Ghost Ledger never stores a Google token. When a letter actually goes out, it exchanges its Auth0 refresh token for a Gmail token that lasts minutes.
- **Nothing is sent without her phone.** Every letter and every reminder starts a **CIBA request with Guardian push**. The message names the bank and the account ending ("Send claim letter to Malnad Co-operative Bank 7703"), so she knows exactly what she's approving. Deny, and nothing is sent. Ignore it, and it asks again the next day.

In my test run, I approved the push for the Nilgiri Life claim. The letter left my Gmail, and I replied from my college account playing the insurer: *"Your claim reference is NL/CLM/2026/0412."* Within a minute the workflow read the reply from the Gmail thread and closed the claim as **answered**.

### 5. A .tech home

The project lives at **[ghostledger.tech](https://ghostledger.tech)**, using the free domain from Hacktoberfest. It shows the results above, the method, and Gemma's full report for Raghavendra. The page is styled like a *bahi-khata*, the red cloth-bound ledger Indian families have kept accounts in for generations.

### What it doesn't do (yet)

- **Both estates are synthetic.** I wrote them to look like real Indian retirees' mail, but real mailboxes are messier. The next step is a Google Takeout import tested with a family who agrees to it.
- **The claim routes are general guidance** from RBI, SEBI, AMFI, IEPF and EPFO rules, not legal advice. Amounts and thresholds change, and the report says to confirm with the institution.
- **About 20 seconds per email on a CPU** is fine for a few hundred emails overnight. It's slow for 20 years of mail, which is why the filter exists.

## Why Does Open Innovation Matter?

A dead parent's mailbox is the most private dataset a family will ever hold. Their health, their money, their arguments and their last few months are all in it. The honest alternative to Ghost Ledger is a service that asks a grieving daughter to upload all of that to a company, and that's not something I would ask of anyone.

**Open weights** are what let Gemma run on an ordinary laptop with the Wi-Fi off. **Open code** means a family, their lawyer or a curious nephew can read every line that touches the mailbox. **Open rules** matter too: the claim routes are public regulations, written down in one file anyone can correct when SEBI changes a threshold, as it recently did.

## My Agent Session

I built Ghost Ledger with Claude as my pair programmer, from the problem research to the code, the evals and the site. I didn't record a DevRelay session. The repository's commit history shows the order things happened, including the commit that froze the held-out estate before Gemma ever read it.

## The Spirit of It

On Día de los Muertos, families lay paths of marigold petals so the dead can find their way home. In India, marigolds garland every funeral. "Ghost in the machine" made me think of the inbox someone leaves behind, still receiving dividend notices, premium reminders and renewal advice for a person who will never open them.

Ghost Ledger is my marigold path, run the other way: it helps what they left behind find its way home to the people they left it for.

## Prize Categories

- **Best Use of Gemma**: Gemma 4 E4B runs locally through Ollama and reads every email, with its output checked by code. Evaluated against a regex baseline on two estates, one held out.
- **Best Use of Temporal**: the durable mailbox scan, plus long-running claim workflows with timers, reminders, replies and escalation. The worker was killed mid-claim and resumed.
- **Best Use of Auth0 for AI Agents**: executor sign-in, Gmail through Token Vault (no Google tokens on disk), and a CIBA + Guardian approval on the phone before every letter.
- **Best Use of a .tech Domain**: [ghostledger.tech](https://ghostledger.tech).
