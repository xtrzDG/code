# Data protection impact assessment (GDPR article 35)

The platform's own assessment of the assistant: what it processes, why
that is necessary, what could hurt the people concerned and which code
stops it. Each business is the controller of its customers' data and
decides on its own DPIA; the help article `docs/help/en/dpia-support.md`
(Italian: `docs/help/it/dpia-support.md`) gives it this material. For the
platform's own processing (accounts, sign-in, billing) the platform is the
controller. The record of processing is `docs/legal/records-of-processing.md`;
categories, classes, transfers and the checked retention periods are in
`docs/security/data-classification.md`.

**Why an assessment.** The Garante's list of processing that needs one
(provvedimento n. 467 of 11 October 2018) names innovative technology
(item 8: AI, voice assistants) when another criterion comes with it; here
there are several: call recordings and transcripts, data of many
customers of many businesses, health details customers volunteer (a
clinic, allergies in a booking), and marketing to the customers the
assistant met.

Reviewed: 2026-11-02. Review again with every new channel, sub-processor,
model provider or kind of personal data, and at least once a year.

## The processing

| Operation | Personal data | Purpose | Code |
| --- | --- | --- | --- |
| The assistant answers chats and messengers | messages, voice notes, photos, names, phones, messenger ids | answer and book for the business | `app/use_cases/conversations/replies/` |
| The assistant answers calls | call audio, transcripts, caller number | the same by phone | `app/adapters/voice/`, `app/use_cases/voice/` |
| Call recordings (off until the owner turns them on) | recordings | the business's own review | `app/adapters/recordings/encrypted_object_recording_storage_adapter.py` |
| Contacts and the team's card | name, phones, channel ids, tags, VIP, block, marketing consent | one customer across channels | `app/schemas/domain/contacts.py` |
| Bookings, requests, handoffs | dates, party, notes (allergies possible) | the business's bookings | `app/use_cases/bookings/` |
| Rebooking campaigns | contact, language, past visit | invite back, recall, pre-arrival notes, only with consent | `app/use_cases/campaigns/campaign_writer.py` |
| Quality sampling (owner may turn off) | a sample of conversations, phones and e-mails blanked | the assistant's quality | `app/utilities/quality/quality_prompts.py` |
| Owners' and staff accounts | phone or e-mail, sign-in codes, sessions, devices, IP | sign-in and security (platform as controller) | `app/use_cases/users/otp_login/` |

## Necessity and proportionality

- **Minimisation.** Recordings are off by default and announced on the
  call (`app/utilities/conversations/assistant_texts/call_texts.py`; where
  every party's consent is the law, the caller may decline:
  `call_consent_texts.py` and the `decline_recording` tool). A reply never
  carries another person's phone or e-mail (`personal_data_check.py` in
  `app/use_cases/conversations/replies/`). Quality samples leave without
  phones and e-mails. Model call records live 30 days at most.
- **Lawful basis.** For customers' data the business's: the contract (a
  booking) or legitimate interest (answering an enquiry). Marketing needs
  the customer's consent (Codice privacy art. 130): an unticked box on the
  booking page or a consent given in person and recorded by the team, each
  stored with when, where, who and the wording's version
  (`MarketingConsent` in `app/schemas/domain/contacts.py`,
  `MarketingConsentText` in `app/schemas/constants/marketing_consent.py`).
  There is no e-mail channel to customers, so the e-mail soft opt-in of
  art. 130(4) never applies; customers from before consent was kept read
  as without consent.
- **Transparency.** The assistant says it is the business's AI assistant
  (AI Act art. 50(1): `ai_disclosure_texts.py`); the hosted chat and the
  booking page link the business's privacy notice
  (`web/src/app/c/[slug]/privacy/`).
- **Rights.** Export and erasure of one customer
  (`app/use_cases/compliance/export_contact_data_use_case.py`,
  `delete_contact_data_use_case.py`, after a fresh sign-in); objection to
  marketing by unticking the box, telling the team, or STOP in a
  messenger (where the campaign's messages arrive: `PROACTIVE_CHANNELS`,
  `app/use_cases/shared/proactive_routes.py`), which also takes the
  consent back for good (`consent_after_save` in
  `app/utilities/customers/customer_card.py`). An erasure stays done after
  a restore from backup (the erasure ledger, below).
- **Retention.** Every period with the job that enforces it, sign-in-code
  challenges (24 hours) and delivery logs (30 days) included:
  `docs/legal/records-of-processing.md`, "Retention".

## Risks and measures

Likelihood and severity before the measures: L low, M medium, H high.

| Risk to people | Before | Measures (where in the code) | Residual |
| --- | --- | --- | --- |
| The AI states wrong facts (prices, allergens, opening hours) and a customer relies on them | M / M | answers only from the business's facts; a reply's claims are checked against evidence before it is sent (`app/utilities/reply_guard/`, `reply_review.py`); unanswerable questions go to the team (handoffs) | L |
| The AI reveals another customer's data | M / H | per-business row-level security for every table (`migrations/1200_tenant_and_platform_roles.sql`, probed by the restore drill), the business of a message comes from the server-side channel lookup, `personal_data_check.py` withholds foreign phones and e-mails | L |
| Instructions hidden in a customer's message steer the AI | M / M | tools act only within the conversation's business and customer; names a customer gives cannot pose as markup (`CustomerGivenName`); every booking change goes through the same use cases as staff's | L |
| A call recording or transcript leaks | L / H | off by default; AES-256-GCM per business and per file (`app/utilities/security/recording_encryption.py`) in an EU bucket; retention purge (`purge_expired_recordings_use_case.py`); access audited | L |
| Conversation content stays at a sub-processor | M / M | models and voice in EU residency; traces at Langfuse 30 days; every erasure and purge deletes the copies by retried jobs (`app/facilitators/privacy/processor_erasure_facilitator.py`); only the uses the registry names (`app/registries/legal/processor_use_catalog.py`) | L |
| Health details (special categories) in notes or calls | M / H | Restricted class, minimisation and the business's retention; never used to train models; the help article tells owners to keep a legal basis | M (the business's DPIA) |
| Marketing without consent, or after it was taken back | M / M | campaigns write only to an active consent (`campaign_writer.py`); STOP, the suppression list and a block always win; a new STOP takes the consent back in the same storage step; the card never says "agreed" for a stopped customer (`app/use_cases/contacts/marketing_consent_views.py`); every change audited | L |
| An erased customer comes back with a restored backup | L / H | the erasure is recorded outside the database (`record_contact_erasure_use_case.py`, `app/adapters/business_closures/bucket_contact_erasure_ledger_adapter.py`) and applied again daily (`reapply_contact_erasures_use_case.py`); the restore drill counts it | L |
| An owner's or staff account is taken over | M / H | sign-in codes hashed, limited and expiring (`app/utilities/security/one_time_codes.py`); second factor and passkeys; Cloudflare Turnstile on risky sign-ins (`app/clients/turnstile/`); a fresh sign-in for exports and erasures (`StepUpGuardContract`) | L |
| Transfers outside the EEA | M / M | each vendor's safeguard (DPF, SCCs, BCRs) in `docs/operations/vendor-register.md`; Telegram and Meta only when the business turns the channel on; Turnstile sees IP and browser signals only, on risky sign-ins | L |
| Data kept longer than needed | M / L | purge jobs per category, watched by Sentry Crons and `missed_job_runs` | L |
| A breach is noticed late or not told | L / H | the audit log's hash chain (`app/use_cases/compliance/audit_chain/`), alerts, `docs/operations/incident.md` (48 hours to the businesses, 72 hours to the Garante) | L |

## Transfers

| Sub-processor | What it receives | Location and safeguard |
| --- | --- | --- |
| OpenAI (EU data residency) | conversation content for replies | EU |
| ElevenLabs (EU residency) | call audio and transcripts | EU |
| Anthropic | quality samples without phones and e-mails, synthetic autotests | US, SCCs |
| Meta (WhatsApp, Instagram, Messenger) | messages in the channel the customer chose | Ireland, onward to the US under DPF and SCCs |
| Telegram | messages in that channel | outside the EEA, no SCCs: only when the business turns it on |
| Twilio | text-back SMS, sign-in codes | US, Binding Corporate Rules |
| Cloudflare (Turnstile) | IP address and browser signals on risky sign-ins | global network, DPF and SCCs |
| Google (Calendar) | names in booking events, when connected | Ireland, DPF and SCCs |
| Stripe, Flitt | billing of the business (never card numbers stored) | Ireland (DPF, SCCs); Georgia (SCCs) |

The full list with dates, attestations and exit plans is the vendor
register; DPA section 8 publishes it.

## Conclusion

With the measures above the residual risks are low, except health
details, which each business that receives them weighs in its own DPIA.
No prior consultation of the Garante (article 36) is needed. Sign-off:
the privacy lead (the founder unless `docs/operations/contacts.md` names
another person), [name, date].
