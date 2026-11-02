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
| GitHub | source code, no customers' data | medium | US; DPF and SCCs | GitHub's customer agreement | SOC 2 Type II |

"To sign", "to request" and "dated copy to file" are the owner's actions
before launch (`docs/operations/go-live.md`); write the date into the cell
when done. The safeguards follow the DPA (section 7.2); the transfer cells
of `docs/security/data-classification.md` repeat them per data category.

**If the Data Privacy Framework falls.** The EU-US framework is challenged
before the Court of Justice (the Latombe appeal, C-703/25 P). Every vendor
above that relies on it also has SCCs in its DPA, so nothing stops; within
a month of a judgment, re-check each transfer impact assessment and the
supplementary measures (EU regions, encryption, scrubbing) and record it
here.

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
