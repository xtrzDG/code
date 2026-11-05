# AI literacy and security training

The training every person of the platform's team gets before their first
access and again every year (AI Act Article 4; ISO/IEC 27001 A.6.3):
support, sales and engineering alike, contractors included. The joiner
checklist of `docs/operations/offboarding.md` points here; businesses get
their own guidance for their staff in the help article
`docs/help/en/ai-use-guidance.md` (Italian `docs/help/it/ai-use-guidance.md`).
`tests/legal/test_ai_literacy.py` checks that every module below exists,
that every record names a module and a date no more than a year old, and
that this page is reviewed yearly.

Reviewed: 2026-11-03. Owner: the founder (the security owner of
`docs/security/information-security-policy.md`).

## How it runs

About 90 minutes, live or as a read-through with the trainer, then the
short check at the end of each module answered in writing. A person who
joins reads modules 1 to 5 before their first access; everyone repeats
them yearly and after a change the trainer marks as material (a new
channel, a new model provider, an incident). Record each session in the
table at the end the same day.

## Modules

### 1. What the assistant is and what it can do

- It is a language model answering from one business's profile and
  knowledge, with fixed actions (bookings, requests, waitlist, links) and a
  handoff to the team. It does not learn from conversations and is never
  trained on customers' data (DPA 2.3).
- It can be wrong: facts missing from the knowledge, a misheard word on
  the phone, a claim the reply guard did not catch. The platform's
  defences are listed in `docs/security/ai-components.md`; the evals are
  in `evals/`.
- The AI Act roles: the platform is the provider, each business the
  deployer (`docs/security/ai-act-assessment.md`). The disclosure at the
  start of every chat and call is the law, not a setting.

*Check:* name two things the assistant will never do on its own, and where
an owner switches its actions off.

### 2. Its limits and when a person must step in

- Allergens, health, money disputes, complaints, anything the business's
  data does not answer: a person decides.
- Pausing the assistant for one business (Settings → General → Assistant
  controls) and the platform brake for all (`docs/operations/runbooks/platform-brakes.md`).
- Never "fix" a business's answer by writing into its knowledge yourself
  without the owner's request: support access is read-only by default and
  every look is in the business's audit log.

*Check:* a customer says the assistant promised a free table; what do you
do first?

### 3. Prompt injection and social engineering

- Customers' messages, documents, websites and calendar entries are data,
  never instructions; an attacker writes "ignore your rules" into a chat,
  a menu PDF or an e-mail. The tools act only within the conversation's
  business and customer (`docs/security/threat-model.md`).
- Caller ID and a name in a chat prove nothing. Nobody gets another
  customer's data, a changed bank detail, a password reset or an exception
  because they claim to be an owner, a supplier, the police or a colleague.
  Owners prove themselves by signing in; support never asks for codes.
- Phishing aimed at the team: sign-in codes, passkeys, provider consoles
  and the vault are never shared, never typed into a page a message links
  to. Report it in the team chat at once.
- Toll fraud and SMS pumping look like ordinary traffic; the signs and
  the first steps are in `docs/operations/runbooks/irsf-toll-fraud.md` and
  `docs/operations/runbooks/sms-pumping.md`.

*Check:* a caller says they are the owner and asks for yesterday's list of
bookings with phone numbers. What do you answer?

### 4. Data protection

- What is personal data here, its classes and where it may go
  (`docs/security/data-classification.md`); special categories in booking
  notes (allergies, health).
- No customer data into personal tools: no copying conversations into a
  personal AI chat, notes app or e-mail; work only in the cabinet, the
  admin console and the approved providers of the vendor register.
- A customer's request (access, erasure) goes to their business, which
  decides; the platform helps (`docs/operations/runbooks/privacy-requests.md`).
- A suspected breach is reported at once, before anything is fixed
  (`docs/operations/incident.md`, `docs/operations/runbooks/data-breach.md`).

*Check:* where may a transcript be pasted to analyse a bug?

### 5. Incidents and who to call

- Severities and the rota (`docs/operations/on-call.md`), the contacts
  (`docs/operations/contacts.md`), the roles of an incident (lead, scribe,
  communicator, privacy lead) and the clocks (48 hours to the businesses,
  72 hours to the Garante, the PSP's own deadline).

*Check:* who keeps the timeline during an incident?

## Records

One row per person and session. Keep the written answers to the checks
with the person's onboarding records for as long as they work with the
platform and one year after.

A date with "(planned)" is a session not held yet; once held, write the
real date and the names.

| Person | Role | Modules | Date | Trainer | Next refresher |
| --- | --- | --- | --- | --- | --- |
| everyone with access today | founder, contractors | 1-5 | 2026-12-01 (planned) | the founder | a year after the session |
