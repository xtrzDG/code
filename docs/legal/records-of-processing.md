# Records of processing activities (GDPR article 30)

The platform's record, kept in writing and given to the Garante on
request (article 30(4)). Part A is the platform as controller (article
30(1)), part B as processor for each business (article 30(2)). Fields in
square brackets are the operator's details, filled in before production
like the other legal texts (`docs/legal/README.md`). The risks and
measures are assessed in `docs/security/dpia.md`; classes and transfers
are in `docs/security/data-classification.md`.

**Controller / processor:** [operator name, address, VAT number].
**Contact for data protection:** [privacy contact e-mail]; the privacy
lead (the founder unless `docs/operations/contacts.md` names another
person). **Representative in the EU:** not
needed (established in the EU) [or name].

## A. The platform as controller

| Activity | Purpose and basis | People | Data | Recipients | Transfers outside the EEA |
| --- | --- | --- | --- | --- | --- |
| Accounts and sign-in | run the cabinet; contract (art. 6(1)(b)), security (art. 6(1)(f)) | owners, staff, platform admins | name, phone, e-mail, sign-in codes (hashed), sessions, passkeys, TOTP seeds (sealed), devices, IP addresses | Twilio (codes by SMS), the e-mail provider, Meta (codes by WhatsApp), Cloudflare (Turnstile) | Twilio: US, BCRs; Cloudflare: DPF and SCCs (IP and browser signals on risky sign-ins only) |
| Billing | invoices and payments; contract, legal obligation (art. 6(1)(c)) | owners, the businesses' billing contacts | billing details, invoices, payment references (never card numbers) | Stripe, Flitt, the accountant | Stripe: DPF and SCCs; Flitt: Georgia, SCCs |
| Security and audit | detect misuse, prove who did what; legitimate interest | owners, staff, admins, customers named by id | audit entries (ids, IP addresses), security events | none outside the platform | none |
| Operations telemetry | keep the service running; legitimate interest | everyone, scrubbed | errors, traces, metrics (no personal data by design) | Sentry (EU), the OTLP collector (EU) | Sentry's US support access under SCCs |
| Public site and growth | attribution of sign-ups with consent (cookie banner, art. 122 Codice privacy), web vitals | visitors | first-touch campaign tags, referrer host, landing path; vitals buckets | none | none |
| Owner communications | service notices, breach notices (DPA 12.1), sub-processor notices | owners | name, phone, e-mail | the e-mail provider, Twilio | Twilio: BCRs |

## B. The platform as processor (for each business)

**Controllers:** every business with an accepted DPA (the table
`dpa_acceptances`, the business's owners as its contact; Settings →
Data protection). **Sub-processors:** DPA section 8 and
`docs/operations/vendor-register.md`.

| Processing on the business's behalf | People | Data | Sub-processors (location, safeguard) |
| --- | --- | --- | --- |
| The assistant in chats, messengers and the hosted chat page | the business's customers and visitors | messages, voice notes, photos, names, phones, messenger ids, language | OpenAI (EU residency); Meta (Ireland, onward DPF and SCCs); Telegram (no SCCs, only when turned on); Langfuse (EU, traces 30 days) |
| Calls, transcripts and recordings | callers | call audio, transcripts, caller number, recordings (only when the owner turns them on) | ElevenLabs (EU residency); Zadarma or the business's telephony (in transit); EU object storage |
| Contacts and the team's card | customers | name, phones, channel ids, tags, VIP, block, marketing consent (when, where, by whom, wording version) | none beyond storage |
| Bookings, requests, handoffs, waitlist | customers | dates, party, services, notes (allergies possible) | Google Calendar, Cal.com (when connected; Google: DPF and SCCs) |
| Notifications to the team | staff | the booking or request they are told about | the e-mail provider, Twilio, Telegram (staff chats the business chose) |
| Campaigns (marketing, with consent only) | customers who agreed | contact, language, past visit | the channel the customer booked in |
| Quality sampling (the business may turn it off) | customers | sampled conversations, phones and e-mails blanked | Anthropic (US, SCCs) |
| Exports and erasures on request | customers | everything of one customer | none |

## Retention

Each period is enforced by the job named; the constants are the ones
`tests/legal/test_data_classification.py` checks.

| Data | Kept | Deleted by | Defined in |
| --- | --- | --- | --- |
| Sign-in-code challenges | 24 hours | `purge_stale_rows`, daily | `OTP_CHALLENGE_RETENTION_SECONDS`, `app/use_cases/maintenance/purge_stale_rows_use_case.py` |
| Second sign-in steps, passkey challenges | 24 hours | `purge_stale_rows` | same module |
| Delivery logs (the outbox: what was sent to whom) | 30 days | `purge_stale_rows` | `DELIVERY_RETENTION_SECONDS`, same module |
| Webhook receipts and inbox events | 30 days | `purge_stale_rows` | `CHANNEL_RECEIPT_RETENTION_SECONDS` |
| Outbound webhook delivery log | 30 days | `purge_webhook_deliveries` | `app/utilities/integrations/webhook_schedule.py` |
| Missed calls | 90 days | `purge_stale_rows` | `MISSED_CALL_RETENTION_SECONDS` |
| Conversations, notes, transcripts | the business's choice, 30 days to 10 years (730 days by default) | `purge_expired_personal_data`, daily | `app/schemas/domain/business_privacy_settings.py` |
| Records of model calls and their traces | 30 days at most | `purge_expired_personal_data` | `DEFAULT_LLM_TURN_RETENTION_DAYS` |
| Call recordings, files customers sent | the business's choice (90 days by default) | `purge_expired_recordings`, daily | `recording_retention_days`, `app/schemas/domain/businesses.py` |
| Contacts and their marketing consent | until the owner erases the customer or the business is deleted; a consent taken back stays recorded as taken back (proof) | the erasure, `delete_business` | `app/use_cases/compliance/contact_data_eraser.py` |
| The erasure ledger outside the database | ids and the moment of each erasure, as long as a backup older than it can be restored | never by the platform (the bucket key cannot delete) | `app/adapters/business_closures/bucket_contact_erasure_ledger_adapter.py` |
| Audit log | at least 365 days, purged at 1,095 days | `workshop purge-audit-log` | `app/utilities/compliance/audit_retention.py` |
| Invoices | 10 years (civil code art. 2220) | kept when the business is deleted | `app/use_cases/businesses/deletion/delete_business_use_case.py` |
| Backups | 30 daily and 12 monthly copies | `workshop backup` retention | `docs/operations/backup-restore.md` |

## Security measures (article 32)

DPA section 9 lists them as applied; in short: per-business row-level
security (`migrations/1200_tenant_and_platform_roles.sql`), secrets and
recordings sealed with AES-256-GCM (`app/utilities/security/`), backups
encrypted with age in an EU bucket of another provider and proven by a
weekly restore drill, hashed sign-in codes with limits and a second
factor, audited views, exports and erasures in a hash-chained log, and the
incident and breach procedure of `docs/operations/incident.md`.
