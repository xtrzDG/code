# Security and certification roadmap

What the platform deliberately does not do yet, the design it will move
to, and what triggers the move: the certification path buyers ask about
(SOC 2 Type II, ISO/IEC 27001) and the engineering items of the readiness
checklist that need infrastructure, a second person or a lawyer rather
than code alone. Each item names its checklist ids
(`docs/security/readiness-checklist.json`); `tests/legal/test_security_roadmap.py`
checks they exist and that this page is reviewed yearly.

Reviewed: 2026-11-03. Owner: the security owner
(`docs/security/information-security-policy.md`).

## Certification

| Step | What | When | Evidence it builds on |
| --- | --- | --- | --- |
| 1. Readiness (now) | policy, risk register, asset inventory, access reviews, vendor register, incident plan and tabletop, backups with restore tests, change management | before the first paying hotel or chain asks | `docs/security/information-security-policy.md`, `docs/security/risk-register.md`, `docs/operations/` |
| 2. Questionnaires | answer buyers with the prepared set (`docs/security/security-questionnaire.md`) and the public security page | from launch | the questionnaire, `/security` |
| 3. SOC 2 Type I | a point-in-time audit of the controls' design, with a compliance automation tool collecting evidence (access reviews, MFA, change records, backups) | when the first customer contract or a chain requires a report, or at 20 paying businesses | steps 1-2, a second maintainer (independent review) |
| 4. SOC 2 Type II | the same controls proven over a 3 to 6 month window | 6 months after Type I | the evidence tool's history |
| 5. ISO/IEC 27001 | certification of the management system (Statement of Applicability against Annex A), if European enterprise buyers ask for it rather than SOC 2 | when a tender or a chain requires it | the same controls; the risk register becomes the risk treatment plan |

The order follows what Italian hospitality buyers ask for first (a
questionnaire and a DPA), then what chains and their insurers ask
(SOC 2 or ISO 27001). Neither audit is planned before a second person
joins: both need segregation of duties the platform cannot show alone.

## Engineering roadmap

| Item | Checklist | Today | Target design | Trigger | Owner step |
| --- | --- | --- | --- | --- | --- |
| Envelope encryption with a managed key | SEC-04 | channel credentials, calendar tokens and TOTP seeds are sealed with Fernet (AES-128-CBC with HMAC) under the `ENCRYPTION_KEYS` ring held in the hosting provider's secret store; the API and the workers both hold the ring; re-sealing on rotation exists | a key-encryption key in an EU KMS or HSM-backed vault; one data key per record or per business, AES-256-GCM, the wrapped data key stored beside the ciphertext; decryption only in the worker that uses the credential (the API seals, never unseals); revocation at the provider on disconnect and offboarding for every credential type, proven by a test per type | before storing a PSP secret of a business, at SOC 2 Type I, or at 50 businesses | provision an EU KMS (or vault) account and its access policy |
| Separate origins | WEB-07 | the API has its own origin; the cabinet, the marketing site, the hosted chat `/c/` and the booking page `/r/` share the cabinet's origin; customers' media is served from the API's origin with a `sandbox` CSP and `nosniff` | marketing site, customer pages (chat and booking) and the cabinet each on their own host; uploaded media on a separate sandbox domain without cookies; the widget keeps only a session token, cleared when the conversation ends | before a business may upload active content, or at the move to separate Render services for marketing | choose the hostnames, DNS and Render services; a DNS inventory scan for dangling records, and CNAME removal in `docs/operations/offboarding.md` |
| A separate admin origin | AUTHZ-04 | the admin console is `/admin` of the cabinet and the admin API `/v1/admin` of the API; admins must have a passkey in production (`ADMIN_PASSKEY_REQUIRED`), admin sessions idle out after 15 minutes, support access is reasoned, time-boxed, read-only by default and audited | the console and `/v1/admin` served only on an admin host (its own cookie scope and CSP), refused on the public hosts; passkey-only admin sign-in (no app codes) | with the separate origins above, or at the second admin | DNS and a deployment for the admin host; confirm in the quarterly access review that no admin account is shared |
| Independent review of security changes | SDLC-05 | branch protection with required checks is declared and verified daily; CODEOWNERS covers the sensitive paths; `required_approving_review_count` is 0 while one maintainer exists, so the author merges alone | at least one approving review and "Require review from Code Owners" on `main` and `release` | a second maintainer | set both in GitHub and in `.github/repository-settings.json`, export the rulesets |
| Contract set and specific approval | GOV-01 | terms, DPA and privacy texts are English templates with fields to fill; the SLA is a draft (`docs/legal/drafts/sla.md`); the acceptable use rules lack telemarketing, impersonation and voice cloning; no separate approval of onerous clauses at signup | Italian and English texts reviewed by an Italian lawyer; the SLA adopted; an acceptable use policy; a second checkbox at signup recording the specific approval of the clauses of art. 1341(2) c.c. with their version | before the first paying Italian business | the lawyer's review; then the signup checkbox is built (product and code change) |

## Done since the last review

Kept short; the items move here from the table when they ship.

- 2026-11-03: admin passkeys required in production and 15-minute admin
  idle timeout (AUTHZ-04, partly); sub-processor transfer mechanisms
  published (PRIV-02); production backups restored only on the
  platform's EU runner (PRIV-05).
