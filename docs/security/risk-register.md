# Risk register

The business risks of the platform, scored before the treatment in place
and owned by a named role: AI behaviour, telephony fraud, payments,
privacy, security, availability, legal and people. The technical threats
behind them, row by row with code and tests, are in
`docs/security/threat-model.md`; the risks to the people whose data is
processed are in `docs/security/dpia.md`. The policy that asks for this
register is `docs/security/information-security-policy.md`.

Reviewed: 2026-11-03. Review at least once a year, after every SEV1 or
SEV2 incident, and when a channel, provider or kind of data is added.
`tests/legal/test_risk_register.py` fails when the review is more than a
year old, when a score is not likelihood times impact, when a row names
no owner or an unknown checklist item, or when a category below has no
risk.

**Scale.** Likelihood 1 rare, 2 unlikely, 3 possible, 4 likely, 5 almost
certain within a year. Impact 1 negligible, 2 minor (one business
inconvenienced), 3 moderate (several businesses, or money under 1,000
euros), 4 major (a breach to notify, money in the thousands, days of
outage), 5 severe (many businesses' data exposed, a fine, the company at
risk). Score = likelihood × impact; 12 or more is treated first. Owners
are roles of the policy: the security owner and the privacy lead are the
founder until `docs/operations/contacts.md` names others.

## Register

| ID | Risk | Category | Likelihood | Impact | Score | Owner | Treatment in place | Checklist | Residual |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R01 | The assistant states a wrong price, allergen or opening hour and a customer relies on it | AI | 3 | 4 | 12 | security owner | answers only from the business's facts, claims checked before sending (`app/utilities/reply_guard/`), allergen questions without data go to staff, evals (`evals/`) | AI-08, AI-12 | medium: the business's data can be wrong |
| R02 | Instructions in a message, document or web page steer the assistant (free bookings, leaks, rude replies) | AI | 3 | 3 | 9 | security owner | tools scoped to the conversation's business and customer, owner texts fenced (`app/utilities/conversations/owner_text_fencing.py`), memory filtered (`app/utilities/conversations/memory_facts.py`), injection evals | AI-01, AI-04, AI-11 | low |
| R03 | Runaway model or voice costs: endless conversations, abuse or a bug | AI | 3 | 3 | 9 | security owner | per-conversation token and time caps, per-business spend limits, the platform's daily budget brake (`docs/operations/runbooks/platform-brakes.md`) | AI-09, LOG-05 | low |
| R04 | The language model provider is down or degraded | AI | 3 | 4 | 12 | incident lead | fallback provider and circuit breakers (`docs/operations/runbooks/llm-outage.md`), calls fall back to the staff phone | REL-04, VOICE-08 | medium |
| R05 | Toll fraud (IRSF): calls transferred or dialled to premium or international numbers at the platform's cost | telephony fraud | 2 | 5 | 10 | security owner | destinations only from the business's profile and refused for premium, satellite and foreign ranges (`app/utilities/channels/transfer_destinations.py`), concurrency caps, provider spend limits, the playbook (`docs/operations/runbooks/irsf-toll-fraud.md`) | VOICE-02, LOG-05 | low |
| R06 | SMS pumping through sign-in codes or text-backs | telephony fraud | 3 | 3 | 9 | security owner | per-number, per-IP and per-business limits, bot check on risky sign-ins, text-back destination rules (`docs/operations/runbooks/sms-pumping.md`) | VOICE-03, ABUSE-05 | low |
| R07 | A caller spoofs a customer's number to read or change their bookings | telephony fraud | 3 | 3 | 9 | security owner | caller ID never authenticates: changes go through a link sent to the booking's own contact or through staff | VOICE-01 | low |
| R08 | A forged or replayed payment webhook marks a deposit paid | payments | 2 | 4 | 8 | security owner | signatures checked before parsing, events deduplicated, Flitt's status re-queried (`docs/security/payments.md`) | API-02, API-03, PAY-03 | low |
| R09 | Card numbers reach the platform (said on a call, typed in a chat) | payments | 3 | 4 | 12 | privacy lead | the assistant never asks for them; numbers are masked before storage, logs and the model (`app/utilities/privacy/sensitive_numbers.py`); payments only on the PSP's pages | PAY-01, PAY-05 | low |
| R10 | A business's PSP account or the platform's billing account is taken over and payouts redirected | payments | 2 | 4 | 8 | security owner | payment settings owner-only with a fresh sign-in; the PSP accounts' own second factor (owner action) | PAY-06, AUTH-08 | medium until MFA is confirmed on every console |
| R11 | One business sees another's customers (a bug, an injected query) | privacy | 2 | 5 | 10 | privacy lead | row-level security on every tenant table (`migrations/1200_tenant_and_platform_roles.sql`), the authorization matrix tests, the restore drill's isolation probes | AUTHZ-01, AUTHZ-02, AUTHZ-08 | low |
| R12 | A transfer outside the EEA becomes unlawful (the Data Privacy Framework falls) | privacy | 2 | 4 | 8 | privacy lead | SCCs behind every DPF vendor, the transfer register and its exit plan (`docs/operations/vendor-register.md`) | PRIV-02, PRIV-05 | low |
| R13 | Marketing reaches customers without consent, or after they withdrew it | privacy | 2 | 4 | 8 | privacy lead | append-only consent ledger, STOP and suppression always win, quiet hours | CONS-01, CONS-02, CONS-03 | low |
| R14 | A breach is noticed late or notified after the deadlines | privacy | 2 | 4 | 8 | privacy lead | alerts, the incident plan's clocks (`docs/operations/incident.md`), the breach runbook | PRIV-09, REL-07 | low |
| R15 | An owner's, staff member's or admin's account is taken over | security | 3 | 4 | 12 | security owner | sign-in codes limited and expiring, second factor, admin passkeys, fresh sign-in for sensitive actions, notices on changes | AUTH-01, AUTH-07, AUTH-08, ABUSE-01 | low |
| R16 | A secret or key leaks (a commit, a log, a laptop) | security | 2 | 5 | 10 | security owner | secrets inventory and rotation (`docs/security/secrets-inventory.md`), secret scanning, keys never logged | SEC-01, SEC-05 | low |
| R17 | A compromised dependency or CI action ships malicious code | security | 2 | 5 | 10 | security owner | lockfiles, actions pinned to commits, dependency review, SBOM and signed images | SDLC-01, SDLC-02, SDLC-03 | low |
| R18 | The hosting account or region is lost with its database | availability | 1 | 5 | 5 | incident lead | point-in-time recovery, immutable off-site backups at another provider, weekly restore drill (`docs/operations/backup-restore.md`) | REL-02, REL-03 | low |
| R19 | A bad release or migration breaks the service | availability | 3 | 3 | 9 | incident lead | expand-and-contract migrations, smoke tests, one-command rollback (`scripts/rollback.sh`) | REL-08 | low |
| R20 | The contracts are incomplete at launch (DPA fields, SLA, acceptable use, Italian texts) | legal | 4 | 3 | 12 | security owner | drafts ready for the lawyer (`docs/legal/drafts/README.md`), the placeholder counter in CI | GOV-01, PRIV-01 | high until the lawyer's review |
| R21 | One maintainer: no independent review, no cover for holidays or illness | people | 4 | 4 | 16 | security owner | CODEOWNERS and required checks, the rota and contacts, written runbooks; a second maintainer is the owner action | SDLC-05, GOV-03 | high until a second maintainer joins |
| R22 | A key vendor changes terms or exits (Meta's messaging rules, the telephony provider) | supplier | 2 | 3 | 6 | security owner | exit plans per vendor (`docs/operations/vendor-register.md`), messaging template and quality alerts | GOV-02, VOICE-09 | low |

## Accepted risks and exceptions

The residual "medium" and "high" rows above are accepted by the security
owner until their owner action is done; the date of acceptance is the
review date. Write an exception to the policy here with its expiry.

| Date | Risk or exception | Why accepted | Until | Accepted by |
| --- | --- | --- | --- | --- |
| 2026-11-03 | R20, R21 | pre-launch: the lawyer's review and a second maintainer are owner actions of `docs/LAUNCH.md` | launch | the founder |
