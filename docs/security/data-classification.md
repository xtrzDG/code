# Data classification, transfers and retention

What data the platform holds, how sensitive each category is, which
sub-processor receives it and from where, and how long it is kept.
`tests/legal/test_data_classification.py` keeps it true: every retention
period below is compared with the constant the purge job uses, every
transfer cell is filled, and every vendor named here is in the vendor
register (`docs/operations/vendor-register.md`, which holds each vendor's
DPA, attestation and exit plan). The DPA's own wording is sections 3, 7, 8
and 13 of `docs/legal/dpa-2026-10-06.en.md`.

## Classes

| Class | Meaning | Handling |
| --- | --- | --- |
| **Restricted** | Opens other data or harms people when leaked: secrets, sign-in material, recordings, special categories | sealed or hashed at rest, never in logs or traces, never exported except by its owner |
| **Confidential** | Personal data of customers, staff and owners | per-business row-level security, audited views and exports, minimised before any sub-processor |
| **Internal** | The businesses' configuration, billing, operations data | role-based access; may reach monitoring scrubbed |
| **Public** | Published texts and reference data | none |

## Categories and where they go

Role: **P** the platform processes it for the business (processor, DPA);
**C** the platform decides (controller: accounts, billing, security).
Transfers name the sub-processor, its location and the safeguard; "none"
means the data stays in the EU (Render, Frankfurt; EU buckets).

| Category | Examples | Role | Class | Stored | Transfers outside the EEA |
| --- | --- | --- | --- | --- | --- |
| Customer contact details | name, phone, messenger ids, e-mail; a website-chat visitor's IP address, kept in the message's inbox event (30 days, as inbox events below) to cap anonymous bookings per client network | P | Confidential | Postgres; backups | Meta (WhatsApp, Instagram, Messenger: Meta Platforms Ireland, onward to the US under the EU-US Data Privacy Framework and SCCs); Telegram (outside the EEA, no SCCs offered: only when the business turns the channel on and the customer writes there); Twilio (text-back SMS: US, Twilio's Binding Corporate Rules); Google Calendar (names in events: Google Ireland, DPF and SCCs) |
| Conversation content | messages, voice notes, transcripts, the team's notes | P | Confidential (Restricted when it reveals health) | Postgres; Langfuse EU (30 days) | the messenger the customer chose (as above); Anthropic, US, SCCs: only sampled conversations with phones and e-mails removed, from 2026-11-05 and only where the business allows quality sampling |
| Call audio and recordings | the call stream, recordings | P | Restricted | EU object storage, sealed with the business's key | none from ElevenLabs (EU residency); Zadarma carries the audio and the callers' numbers in transit, and its location is still an owner action of the vendor register (its contract) |
| Booking and request details | dates, party size, services, notes (allergies possible) | P | Confidential (Restricted for health notes) | Postgres | Google Calendar when connected (Google Ireland, DPF and SCCs); notifications by e-mail (EU provider) and SMS (Twilio, BCRs) |
| Owner and staff accounts | name, phone, e-mail, Telegram chat id, devices, IP addresses | C | Confidential | Postgres | Twilio (login codes: BCRs); Cloudflare Turnstile (IP and browser signals on risky sign-ins: DPF and SCCs); Telegram (alerts to staff chats, chosen by the business) |
| Sign-in material | sessions, sign-in-code challenges, TOTP seeds, recovery codes, passkey keys | C | Restricted | Postgres, sealed or hashed | none (the code itself travels by SMS, WhatsApp or e-mail as above) |
| Channel and integration credentials | Telegram and Meta tokens, Google refresh tokens, webhook secrets | P | Restricted | Postgres, sealed (`docs/security/secrets-inventory.md`) | none (each goes only to its own provider) |
| The business's knowledge and settings | prices, menus, opening hours, staff names in answers | P | Internal | Postgres | Anthropic (synthetic autotests built from the knowledge: US, SCCs) |
| Billing of the business | invoices, plan, payment references (never card numbers) | C | Internal | Postgres | Stripe (Stripe Payments Europe, Ireland; onward under DPF and SCCs); Flitt (Georgia: SCCs) |
| Audit and security logs | who viewed, exported, erased; sign-ins with addresses | C | Confidential | Postgres, append-only hash chain; Render log drain (EU, 30 days) | none |
| Technical telemetry | errors, traces, metrics, web vitals | C | Internal (scrubbed of personal data) | Sentry EU, the OTLP collector (EU), Prometheus | none (Sentry EU region; Sentry's US support access under SCCs) |
| Backups | everything above, encrypted with age | P and C | Restricted | EU bucket of another provider | none |
| Published content | legal texts, help, catalogs | C | Public | the image | none |

The language models run in OpenAI's EU data residency project and the
voice agent in ElevenLabs' EU residency environment, so the main flows of
conversation content stay in the EU (DPA 7.1). Personal data reach a
sub-processor only for the purposes the registry names
(`app/registries/legal/processor_use_catalog.py`); production refuses to
start otherwise (`tests/legal/test_processor_uses.py`).

## Retention

| Data | Kept | Deleted by | Defined in |
| --- | --- | --- | --- |
| Sign-in-code challenges | 24 hours | `purge_stale_rows`, daily | `OTP_CHALLENGE_RETENTION_SECONDS` in `app/use_cases/maintenance/purge_stale_rows_use_case.py` |
| Second sign-in steps and passkey challenges | 24 hours | `purge_stale_rows` | same module |
| Expired sessions | until their idle or absolute expiry, then the next run | `purge_stale_rows` | `app/utilities/security/session_expiry.py` |
| Delivery logs (outbox messages) | 30 days | `purge_stale_rows` | `DELIVERY_RETENTION_SECONDS` |
| Webhook receipts and inbox events | 30 days | `purge_stale_rows` | `CHANNEL_RECEIPT_RETENTION_SECONDS` (receipts), `DELIVERY_RETENTION_SECONDS` (inbox events) |
| Outbound webhook delivery log | 30 days | `purge_webhook_deliveries`, daily | `app/utilities/integrations/webhook_schedule.py` |
| Facebook sign-ins of the Channels page (the owner's Facebook token while a page is picked) | 15 minutes, then removed by the next daily run | `purge_stale_rows` | `STATE_LIFETIME_SECONDS` in `app/use_cases/channels/meta_connection/meta_states.py` |
| Missed calls | 90 days (sooner with the conversation) | `purge_stale_rows` | `MISSED_CALL_RETENTION_SECONDS` |
| Conversations, notes, transcripts | the business's choice, 30 days to 10 years; 730 days by default | `purge_expired_personal_data`, daily | `DEFAULT_CONVERSATION_RETENTION_DAYS` in `app/schemas/domain/business_privacy_settings.py` |
| Records of model calls (and their Langfuse traces) | 30 days by default, never more | `purge_expired_personal_data` | `DEFAULT_LLM_TURN_RETENTION_DAYS` |
| Call recordings and files customers sent | the business's choice; 90 days by default | `purge_expired_recordings`, daily | `recording_retention_days` of `app/schemas/domain/businesses.py` |
| Leads, bookings, handoffs | anonymised with their conversation (bookings once the visit is over) | `purge_expired_personal_data` | `app/use_cases/compliance/retention/` |
| Customer contacts | until the owner erases them or the business is deleted | the erasure, `delete_business` | `app/use_cases/compliance/delete_contact_data_use_case.py`, `app/use_cases/compliance/contact_data_eraser.py` |
| Marketing consent (when, where, the wording's version, who recorded it; a withdrawal stays recorded) | with the contact, until the erasure | the erasure, `delete_business` | `app/schemas/domain/contacts.py` (`MarketingConsent`) |
| Contact-erasure ledger objects (business and contact ids and the moment, nothing personal) | in the backup bucket beside the business ledger, so a restore can apply them again | nothing in the application: the ledger's key may not delete (`docs/operations/backup-restore.md`, "The bucket") | `app/adapters/business_closures/bucket_contact_erasure_ledger_adapter.py` |
| Full business exports | until the one-time link expires (10 minutes by default) | `purge_business_exports`, hourly | `DEFAULT_EXPORT_DOWNLOAD_LINK_MINUTES` |
| Idempotency keys | 24 hours | `purge_idempotency_keys`, hourly | `IDEMPOTENCY_KEY_LIFETIME` |
| Finished queued jobs | 30 days | `purge_finished_jobs`, daily | `FINISHED_JOB_RETENTION_DAYS` |
| Web vitals | 90 days | `purge_web_vitals`, daily | `WEB_VITAL_RETENTION_SECONDS` |
| Audit log | at least 365 days; purged at 1,095 days | `workshop purge-audit-log --older-than-days 1095`, every January (`docs/operations/maintenance.md`) | `MINIMUM_AUDIT_RETENTION_DAYS` in `app/utilities/compliance/audit_retention.py` |
| A business that stopped paying | its data, 30 days after the end | `offboard_unpaid_businesses`, then `delete_business` | `DEFAULT_OFFBOARD_AFTER_DAYS` |
| Invoices and billing records | 10 years for an Italian seller (civil code, art. 2220) | kept when the business is deleted, with the audit log | `app/use_cases/businesses/deletion/delete_business_use_case.py` |
| Backups | 30 daily and 12 monthly copies | `workshop backup` retention | `docs/operations/backup-restore.md` |
| Render logs | 30 days | the EU log store's retention | `docs/operations/observability.md` |

After a restore, deletions and customers' erasures made since the backup
are applied again (`reapply_deletion_ledger`, `reapply_contact_erasures`),
so a restore never brings an erased customer back.

## Is the retention job running?

Every purge above is a periodic job; a job that stops is noticed five ways:

1. **Sentry Crons**: each periodic run checks in (monitor slug = job name
   with hyphens, e.g. `purge-expired-personal-data`); a missed or failed
   run pages (`app/facilitators/observability/sentry_job_monitor_facilitator.py`).
2. **The system page**: `/admin/system` lists, per worker, the periodic
   jobs whose last run failed (`failing_jobs`).
3. **The run table**: `periodic_job_runs` holds each period's run and
   status; the monthly check in `docs/operations/maintenance.md` reads
   the last `succeeded` run of each purge job.
4. **The audit log**: each purge that removed rows writes
   `retention_purge` with its counts, without an actor.
5. **The platform alert** `missed_job_runs` (SEV2): a shared periodic job
   that has not succeeded within its interval plus a grace pages without
   Sentry (`periodic_job_heartbeats`,
   `docs/operations/runbooks/missed-job-runs.md`).

No worker at all is `worker_down` (SEV1, `docs/operations/slo.md`).
