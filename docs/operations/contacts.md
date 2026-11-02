# Contacts: the team, the providers and the authorities

Who to call during an incident. Personal phone numbers stay in the paging
service (`docs/operations/go-live.md`, step 9), never in this repository;
the fields in square brackets are the owner's to fill at launch and to
check in the quarterly access review (`docs/security/access-review.md`).

## The team

| Role | Who | Reaches | Holds |
| --- | --- | --- | --- |
| Founder (platform owner) | [name] | the paging service; [e-mail] | Render, GitHub organisation, every provider console, the registrar, the password manager vault; the final say on breach notices |
| Deputy (second maintainer) | [name] | the paging service; [e-mail] | Render and GitHub (deploy, rollback, restore, key rotation); provider consoles read-only plus key rotation |
| Privacy lead | [name; the founder until another person is named] | [phone in the paging service]; [e-mail] | the breach risk assessment, the Garante notification and the breach register (`docs/operations/incident.md`), the DPIA (`docs/security/dpia.md`) and the records of processing (`docs/legal/records-of-processing.md`) |
| Rota primary and secondary | the week's rota | the paging service | as their roles above |
| Security mailbox | `SECURITY_CONTACT_EMAIL` (`web/src/server/securityTxt.ts`) | read every working day | vulnerability reports (`SECURITY.md`) |
| Support mailbox | `GET /v1/support/contacts` | read every working day | owners' questions, data subject requests passed on (DPA 11.3) |

## Providers

Each provider's support channel and status page; the account it is
reached from is the founder's unless the vendor register says otherwise
(`docs/operations/vendor-register.md`). Open a ticket at the start of a
provider incident and write its number in the timeline.

| Provider | What breaks without it | Status page | Support |
| --- | --- | --- | --- |
| Render (API, workers, database, cron) | everything | https://status.render.com | the dashboard's support form; [plan's support e-mail] |
| OpenAI (EU project) | the assistant's replies, voice notes, knowledge search | https://status.openai.com | https://help.openai.com |
| Anthropic | the fallback model, autotests' judge | https://status.anthropic.com | https://support.anthropic.com |
| ElevenLabs | the voice agent | https://status.elevenlabs.io | [enterprise support e-mail from the contract] |
| Zadarma | the phone numbers and call forwarding | [none public] | support from the Zadarma cabinet; [account manager] |
| Twilio | SMS codes, text-backs, the voice fallback | https://status.twilio.com | the console's support; [account SID in the vault] |
| Meta (WhatsApp, Instagram, Messenger) | those channels, WhatsApp codes | https://metastatus.com | Meta Business Help Center, direct support of the Business Manager |
| Telegram | the Telegram channels, alerts to the ops chat | [none official] | https://t.me/BotSupport |
| E-mail provider | login codes by e-mail, notices, alerts by e-mail | [provider's status page] | [provider's support] |
| Stripe | subscriptions, deposits | https://status.stripe.com | the dashboard's support |
| Flitt | payments where Flitt is the PSP | [none public] | [merchant support from the contract] |
| Google (Calendar) | calendar sync | https://www.google.com/appsstatus | Google Cloud console support |
| Cloudflare (Turnstile, DNS when used) | bot checks of risky sign-ins | https://www.cloudflarestatus.com | the dashboard's support |
| Sentry (EU) | error reports, Crons | https://status.sentry.io | the dashboard's support |
| Langfuse (EU) | the quality journal | https://status.langfuse.com | support e-mail of the plan |
| Object storage (EU) | recordings, backups | [provider's status page] | [provider's support] |
| Registrar and DNS host | every public host | [provider's status page] | [provider's support] |
| GitHub | CI, deploys of new releases | https://www.githubstatus.com | GitHub support |

## Authorities

| Authority | When | How |
| --- | --- | --- |
| Garante per la protezione dei dati personali (Italy) | a personal data breach where the platform is controller (accounts, billing, security data): within 72 hours; for the businesses' data each business notifies, the platform helps (DPA 12.2) | the online data breach procedure on https://servizi.gpdp.it; Piazza Venezia 11, 00187 Roma; protocollo@pec.gpdp.it; +39 06 696771 |
| The lead authority of another country | a breach of a business outside Italy | the business notifies its own authority; the platform gives it the DPA 12.1 notice |
| CSIRT Italia (Agenzia per la cybersicurezza nazionale) | a significant incident, only once the platform is in scope of NIS2 (D.Lgs. 138/2024); the assessment is still open (`docs/security/readiness-checklist.json`, GOV-08, the regulatory applicability register) | https://www.csirt.gov.it |
| Polizia Postale e delle Comunicazioni | fraud, extortion, a compromise by a known attacker | https://www.commissariatodips.it |

Every notice to an authority is recorded in the incident's timeline with
the time it was sent and the reference it received.
