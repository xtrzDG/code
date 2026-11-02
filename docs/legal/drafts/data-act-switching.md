# Switching and data export (Data Act Chapter VI) — draft, needs_review

Not a published text and nothing in the product serves it. It collects, for
the reviewing lawyer and for the switching information the operator must
publish before contracting (Regulation (EU) 2023/2854, art. 23, 25, 26, 29;
GDPR art. 20 and 28(3)(g)), what the platform does today and the clauses
the next terms version should carry. Fields in square brackets are the
lawyer's and the operator's to decide.

## 1. What the client can take along (implemented)

**Settings → Privacy → Export your data → Prepare full export** (owners only, after a fresh sign-in or
a second factor; audited) writes one ZIP archive. The worker builds it in
the background; one-time links download it up to 3 times within 24 hours
(`app/use_cases/exports/`). An owner may ask again at any time, also
during a closure's 30 days.

The archive is **format 2** (the README inside names it; a changed layout
is a new number):

| File | What it holds |
| --- | --- |
| `README.txt` | The business, when the archive was made, the format number |
| `business.json` | The business: name, time zone, languages, members, plan |
| `contacts.json` | Customers (erased ones and test-chat contacts left out) |
| `conversations.json`, `messages.json` | Every conversation and message |
| `calls.json` | Every call: times, numbers, transcript, summaries, outcome |
| `bookings.json`, `leads.json`, `handoffs.json` | Bookings, requests, transfers to staff |
| `resources.json`, `knowledge_items.json` | Tables or rooms, the knowledge base |
| `missed_calls.json`, `feedback_requests.json` | Missed calls, ratings asked and given |
| `waitlist_entries.json`, `campaign_messages.json` | The waitlist, the return-visit messages |
| `audit_log.json` | Who viewed or changed personal data |
| `business_profile.json` | What the setup was told: hours, rules, links, tone |
| `assistant_versions.json` | Every version of the assistant: its instructions (`prompt_text`, `phone_prompt_text`), tools, languages, facts |
| `call_settings.json`, `privacy_settings.json` | Settings → Calls and Settings → Privacy |
| `channels.json` | The connected channels, **without** credentials or WhatsApp PINs |
| `consent_records.json` | The consent ledger: every marketing consent and withdrawal |
| `recordings/<call id>.<ext>` | The calls' audio (mp3, wav, ogg, webm, m4a or bin) |
| `recordings.json` | Every recording: `status` `included` / `left_out` (past the archive's 2 GiB of audio) / `unavailable` / `incomplete`, its `file`, `media_type`, `total_bytes` and the `download_path` that downloads it while the account is open |
| `csv/*.csv` | The cabinet's tables (bookings, leads, contacts, conversations, audit log) as their downloads: UTF-8 with BOM, local times |

Every JSON file is an array of the documents as the platform stores them,
each with its `schema_version`; times are UTC microseconds since
1970-01-01; ids are the platform's own (`contact_…`, `call_…`), and records
point to each other by them (a message's `conversation_id`, a booking's
`contact_id`). The stored shapes of every version are recorded in
`tests/storage/document_schemas/` with a golden example per version in
`tests/storage/golden/`; that is the machine-readable schema a receiving
provider validates against. Secrets never leave: channel tokens and PINs,
review link tokens.

Single customers: **Customers → a customer → Export** gives one customer's
records as JSON (GDPR art. 15 and 20), consent ledger included.

## 2. After the end (implemented)

Closing the business (Settings → General) starts 30 days during which the
full export stays available and the closure can be cancelled; then the
business's data is deleted in stages and a deletion certificate (PDF) is
issued (`app/use_cases/businesses/closure/`,
`app/use_cases/businesses/deletion/`). What the law keeps (issued invoices,
the audit log until its retention purge) is listed on the certificate.

## 3. Clauses the next terms version should carry (owner action)

The published terms (`terms-2026-10-05.en.md`, 8.2 and 11.2) say only that
the client may export at any time and for "[30] days" after the end. Data
Act art. 25 and 29 require, before the client signs:

1. **Notice**: the client may ask to switch or to leave with at most
   [2 months'] notice.
2. **Transitional period**: at most [30 days] from the notice, during which
   the service continues unchanged and the export above stays available;
   extendable once by the client when it gives reasons.
3. **Retrieval period**: at least [30 days] after the transitional period,
   during which the client can still download everything (today: the 30
   days of a closure).
4. **Erasure**: then complete erasure, confirmed by the deletion
   certificate.
5. **Charges**: no switching or export charges from 12 January 2027;
   before that only charges that do not exceed the provider's costs
   [state them, or "none"].
6. **Disclosure**: the procedure, the formats (section 1) and the known
   limits (no export of the voice agent's internal configuration at the
   voice platform, which belongs to the provider; recordings past 2 GiB are
   downloaded one by one) are published before contracting, e.g. as an
   annex of the terms and a help article.

## 4. Open points for the operator

- Decide whether a closure's 30 days count as the transitional period
  (service continues) or as the retrieval period (today the assistant
  stops answering when the business is closed); if both are needed, the
  closure clock must grow to [30 + 30] days.
- Publish this information before contracting (art. 26) and keep it in
  step with `ARCHIVE_FORMAT` in `app/use_cases/exports/business_archive.py`.
