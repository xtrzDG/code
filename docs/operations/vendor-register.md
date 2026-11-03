# Vendor register

Every outside service the platform depends on: what it gets, how critical
it is, where it processes data and under which safeguard, the contract and
the reports kept on file, and how we would leave it. The sub-processors the
businesses see are the registry of `app/registries/legal/` (DPA section 8);
`tests/legal/test_operations_documents.py` fails when a sub-processor of the
registry is missing here, or when the yearly review is overdue.

Reviewed: 2026-11-02. A vendor is assessed with this table before it joins
(and before its DPA section 8 entry is announced), and the whole register is
reviewed every January (`docs/operations/maintenance.md`).

**Criticality.** *Critical*: without it no business gets answers.
*High*: a channel, a feature or the money stops. *Medium*: degraded, with a
workaround. *Low*: comfort or insight only.

## Register

| Vendor | Gets | Criticality | Location and safeguard | DPA | Reports to keep on file |
| --- | --- | --- | --- | --- | --- |
| Render | all data of the service (hosting, Postgres, cron) | critical | Frankfurt; Render Services (US) under SCCs for support access | Render's online DPA; dated copy to file | SOC 2 Type II |
| OpenAI (EU project) | messages, voice notes, knowledge, booking details | critical | EU data residency | OpenAI's DPA (OpenAI Ireland) with SCCs; dated copy to file, zero data retention to request | SOC 2 Type II |
| Anthropic | knowledge (autotests); messages only after a switch; scrubbed samples from 2026-11-05 | high | US; SCCs of Anthropic's commercial DPA | online DPA; dated copy to file | SOC 2 Type II, ISO 27001 |
| ElevenLabs | call audio, transcripts, caller numbers | high | EU residency environment | DPA with the EU residency terms; to file | SOC 2 Type II |
| Zadarma | caller and called numbers, audio in transit | high | to confirm in the contract (EU entity expected) | to sign | to request |
| Twilio | phone numbers, SMS contents, the voice fallback | high | US and Ireland; Twilio's Binding Corporate Rules, DPF | Twilio's online DPA; dated copy to file | ISO 27001, SOC 2 Type II |
| Meta (WhatsApp, Instagram, Messenger) | messages, user ids, WhatsApp numbers | high | Meta Platforms Ireland; onward to the US under DPF and SCCs | Meta's Data Processing Terms (accepted with the platform terms) | none issued for the platform terms |
| Telegram | messages, user ids of the Telegram channel; ops alerts | high | outside the EEA; no safeguard offered | none offered: the business turns the channel on, the DPIA support pack names the risk | none |
| E-mail provider (SMTP) | owners' addresses, notices with customer names | high | an EU provider to choose before launch | to sign | to request |
| Stripe | billing data of the businesses, deposits (cards never reach us) | high | Stripe Payments Europe (Ireland); onward under DPF and SCCs | online DPA; dated copy to file | PCI DSS Level 1, SOC 2 Type II |
| Flitt | billing data where Flitt is the PSP | high | Georgia; SCCs | to sign (SCCs annexed) | PCI DSS certificate |
| Object storage (EU) | recordings, files, encrypted backups | high | an EU provider other than Render | to sign | to request |
| Google (Calendar) | booking times, customer names in events | medium | Google Ireland; onward under DPF and SCCs | Google Cloud's data processing terms; dated copy to file | ISO 27001, SOC 2 Type II |
| Cloudflare (Turnstile) | IP address and browser signals on risky sign-ins | medium | global network; DPF and SCCs | Cloudflare's online DPA; dated copy to file | ISO 27001, SOC 2 Type II |
| Langfuse | prompts and replies (30 days) | low | EU region (Germany) | online DPA; dated copy to file | SOC 2 Type II, ISO 27001 |
| Sentry | error data, scrubbed | low | EU region; Functional Software (US) under DPF and SCCs for support access | online DPA; dated copy to file | SOC 2 Type II |
| Web push services (Google, Mozilla, Apple) | a device's push address; end-to-end encrypted notices | low | outside the EEA under each vendor's terms | none (browser infrastructure) | none |
| Registrar and DNS host | no personal data | critical | [provider] | not needed | not needed |
| GitHub | source code and CI; no customers' data (production's backups are restored only on the platform's EU drill machine) | medium | US; DPF and SCCs | GitHub's customer agreement | SOC 2 Type II |

"To sign", "to request" and "dated copy to file" are the owner's actions
before launch (`docs/operations/go-live.md`); write the date into the cell
when done. The safeguards follow the DPA (section 7.2); the transfer cells
of `docs/security/data-classification.md` repeat them per data category.

**GitHub and the restore drill.** Decision of 2026-11-03: GitHub-hosted
runners restore only a seeded, synthetic database
(`.github/workflows/restore-drill.yml`, job `round-trip`). The weekly
restore of production's newest backup runs on the platform's drill machine
in the EU (`docs/operations/backup-restore.md`, "Where the production
drill runs"), so GitHub is no sub-processor and not in the DPA's list. The
workflow's `production` job, which would decrypt production's data on a
GitHub-hosted runner, stays off (`RESTORE_DRILL_ON_GITHUB` unset); turning
it on is a transfer to GitHub (US, its DPA with DPF and SCCs) that must
first be announced in the DPA's list with 30 days' notice. Until then the
`backup-drill` environment's copy of the drill's private age key is not
needed and can be deleted (it opens backups but reaches no bucket by
itself). The drill machine's own provider sees production's data
decrypted, so it is a sub-processor too: it gets the drill's key only once
the DPA's list names it for the restore test (the backup bucket's
provider, its object storage entry widened and announced 30 days ahead;
`docs/operations/backup-restore.md`, "Where the production drill runs").

**If the Data Privacy Framework falls.** The EU-US framework is challenged
before the Court of Justice (the Latombe appeal, C-703/25 P). Every vendor
above that relies on it also has SCCs in its DPA, so nothing stops; within
a month of a judgment, re-check each transfer impact assessment and the
supplementary measures (EU regions, encryption, scrubbing) and record it
here.

## Transfer register

Each sub-processor's transfer mechanism as the DPA's list publishes it
(`transfer_mechanisms` of `app/registries/legal/`, rendered into DPA
section 8 and `GET /v1/legal/subprocessors`), the day it was recorded from
the vendor's terms, and the evidence to keep on file. A vendor processing
in the EEA with no access from elsewhere has no row.
`tests/legal/test_subprocessor_transfers.py` fails when the registry and
this page disagree, or a row is more than a year old: re-check each
mechanism against the vendor's current DPA and the official DPF list
(dataprivacyframework.gov) every January, and write the new date.

| Vendor | Mechanism | Recorded | Evidence on file |
| --- | --- | --- | --- |
| Render | SCCs (support access from the US) | 2026-11-03 | dated DPA copy; transfer impact assessment (TIA): to write |
| OpenAI | SCCs in OpenAI Ireland's DPA (access from the US to the EU project) | 2026-11-03 | dated DPA copy; TIA: to write; screenshot of the project's EU residency setting |
| Anthropic | SCCs of the commercial DPA | 2026-11-03 | dated DPA copy; TIA: to write |
| Twilio | Binding Corporate Rules; DPF | 2026-11-03 | dated DPF list screenshot: to file; BCR approval reference |
| Meta | DPF; SCCs | 2026-11-03 | dated DPF list screenshot: to file; TIA: to write |
| Telegram | none offered: only when the business turns the channel on | 2026-11-03 | the DPIA support pack's warning (`docs/help/en/dpia-support.md`) |
| Stripe | DPF; SCCs (onward from Ireland) | 2026-11-03 | dated DPF list screenshot: to file |
| Flitt | SCCs (Georgia has no adequacy decision) | 2026-11-03 | signed DPA with SCCs annexed: to file; TIA: to write |
| Google (Calendar) | DPF; SCCs (onward from Ireland) | 2026-11-03 | dated DPF list screenshot: to file |
| Cloudflare (Turnstile) | DPF; SCCs | 2026-11-03 | dated DPF list screenshot: to file |
| Sentry | DPF; SCCs (support access from the US) | 2026-11-03 | dated DPF list screenshot: to file |
| Web push services (Google, Mozilla, Apple) | none offered: browser infrastructure, end-to-end encrypted notices | 2026-11-03 | none |
| Zadarma | to be confirmed in the contract | 2026-11-03 | the contract naming the processing location: to sign |

## Exit plans

| Vendor | How we leave or survive its loss |
| --- | --- |
| Render | the backend is one Docker image (`Dockerfile`) and the cabinet another (`web/Dockerfile`); `render.yaml` maps every service; restore the newest off-site backup into any Postgres 16 with pgvector (`docs/operations/backup-restore.md`, "Restore runbook") |
| OpenAI | `LLM_PROVIDER=anthropic` (the fallback already answers during an outage: `runbooks/llm-outage.md`); embeddings are optional (`EMBEDDINGS_API_KEY` unset) |
| Anthropic | `LLM_FALLBACK_MODEL_ID` to another OpenAI model or `off`, `LLM_JUDGE_MODEL_ID` to an OpenAI model, `QUALITY_SAMPLING_JUDGE_SAME_PROVIDER` on |
| ElevenLabs | rented numbers put calls through to the staff mobile on duty (Twilio's voice fallback, `app/gateways/http/twilio_voice_routes.py`) while a replacement agent is set up (`runbooks/voice-outage.md`) |
| Zadarma | the business's number is rented from Twilio instead (`PHONE_NUMBER_PROVIDER=twilio`, imported into the voice platform natively) and the call forwarding moved to it |
| Twilio | login codes go by WhatsApp, Telegram or e-mail; text-backs pause |
| Meta, Telegram | no substitute for the channel itself; customers reach the business through the website chat, the hosted chat page and the phone |
| E-mail provider | any SMTP service: change `SMTP_*`, then SPF, DKIM and DMARC of the sending domain |
| Stripe, Flitt | both are implemented and chosen per country (`PaymentProviderRegistry`); leaving one moves its countries to the other, and owners enter a payment method again |
| Object storage | any S3-compatible EU bucket: copy the objects, change `RECORDINGS_S3_*` / `BACKUP_S3_*` |
| Google (Calendar) | optional: owners keep the cabinet's own calendar |
| Cloudflare (Turnstile) | the bot check is one client (`app/clients/turnstile/`); replace it behind the same contract |
| Langfuse, Sentry | optional: unset their variables; logs and Prometheus remain |
| Web push services | optional: owners still get their notices by e-mail, Telegram or WhatsApp |
| Registrar and DNS host | transfer the domain; keep the zone file exported in the vault |
| GitHub | git history is portable; CI workflows are YAML in `.github/workflows/` |
