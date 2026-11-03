# Security questionnaire: prepared answers

Answers to the questions hotels, chains and their IT providers ask before
buying (the common ground of CAIQ-Lite, SIG Lite and the Italian
hospitality chains' supplier forms), ready to paste and kept true by the
documents they cite. Answer only from this page and the documents it
names; a question not here goes to the security owner. "Not yet" answers
are deliberate: never improve them in a reply. Public summary: the
security page of the website (`docs/legal/security-2026-10-05.en.md`).

Reviewed: 2026-11-03. Review with every release that changes a cited
document, and at least every six months. `tests/legal/test_security_questionnaire.py`
checks that every answer cites evidence that exists.

## Organisation and governance

| # | Question | Answer | Evidence |
| --- | --- | --- | --- |
| 1 | Do you have an information security policy? | Yes, approved by the founder, reviewed yearly and acknowledged by everyone with access. | `docs/security/information-security-policy.md` |
| 2 | Do you keep a risk register? | Yes: likelihood, impact, owner and treatment per risk, AI, telephony fraud, payments and privacy included, reviewed yearly. | `docs/security/risk-register.md` |
| 3 | Do you hold SOC 2 or ISO 27001? | Not yet. The controls are documented and evidenced; a SOC 2 Type I is planned when customers require it (roadmap). Vendor reports (Render, OpenAI, Stripe and others) are available on request. | `docs/security/roadmap.md`, `docs/operations/vendor-register.md` |
| 4 | Is staff trained on security and AI? | Yes, before first access and yearly, with records. | `docs/security/ai-literacy.md` |
| 5 | Which laws apply to you? | GDPR (processor and controller), the AI Act (provider of a limited-risk system), the Data Act switching rules, the Italian Codice privacy; NIS2 and the CRA do not apply today. | `docs/security/regulatory-register.md` |

## Data protection

| # | Question | Answer | Evidence |
| --- | --- | --- | --- |
| 6 | Do you sign a DPA? | Yes, every business accepts the Art. 28 DPA in the cabinet; the accepted version and time are recorded. | `docs/legal/dpa-2026-10-06.en.md`, `docs/legal/drafts/dpa-art28-annex.md` |
| 7 | Where is our data stored? | In the EU: application and database in Frankfurt; language model and voice in EU residency; backups at another EU provider. | `docs/security/data-classification.md` |
| 8 | Which sub-processors do you use, and under which transfer mechanism? | The public list gives purpose, location and mechanism for each, with 30 days' notice of changes. | `GET /v1/legal/subprocessors`, `app/registries/legal/` |
| 9 | Do you train AI models on our data? | No, and the model providers' contracts exclude training. | DPA 2.3, `docs/security/ai-components.md` |
| 10 | Can we export and delete data? | Yes: per customer and for the whole business, from the cabinet; deletion reaches the sub-processors' copies and comes with a certificate. | `docs/help/en/privacy.md` |
| 11 | Do you have a DPIA? | Yes for the platform; businesses get a DPIA support pack. | `docs/security/dpia.md`, `docs/help/en/dpia-support.md` |
| 12 | How long do you keep data? | Per category, each enforced by a job; recordings 90 days by default, conversations as the business sets. | `docs/legal/records-of-processing.md` |

## Access control

| # | Question | Answer | Evidence |
| --- | --- | --- | --- |
| 13 | How do users sign in? | One-time codes by phone or e-mail, optional second factor (TOTP or passkey) that an owner can require for the whole team; passkeys required for platform admins in production. | `docs/security/runtime-protections.md` |
| 14 | Can your staff see our data? | Only through a support access the business can see: a recorded reason, 60 minutes, read-only unless the owner allowed changes, shown with a banner and in the audit log. | `docs/security/permission-matrix.md` |
| 15 | Are tenants isolated? | Yes: row-level security in the database for every business's table, tested for every route and probed by the weekly restore drill. | `migrations/1200_tenant_and_platform_roles.sql`, `docs/security/threat-model.md` |
| 16 | Do you review access? | Every quarter; leavers lose access within 24 hours. | `docs/security/access-review.md`, `docs/operations/offboarding.md` |
| 17 | Is there an audit log we can see? | Yes: views, exports, erasures, settings and support access, hash-chained. | `docs/security/log-inventory.md` |

## Application and infrastructure security

| # | Question | Answer | Evidence |
| --- | --- | --- | --- |
| 18 | Is data encrypted in transit and at rest? | TLS everywhere; recordings and credentials sealed at the application level; database and backups encrypted. Credentials use application-level encryption with keys in the hosting provider's secret store; a managed KMS is on the roadmap. | `docs/security/secrets-inventory.md`, `docs/security/roadmap.md` |
| 19 | How do you develop securely? | Pull requests with a risk class, required checks (tests, types, static analysis, dependency, secret and image scanning), signed images and provenance. Independent review of every change starts with a second maintainer (roadmap). | `SECURITY.md`, `docs/security/change-risk.md` |
| 20 | Do you run penetration tests? | Automated web scans (DAST) run on every release candidate and weekly, with an active scan of staging; no external penetration test yet: it is an owner decision before the first enterprise contract. | `SECURITY.md`, `docs/security/roadmap.md` |
| 21 | How do you protect the AI assistant from abuse? | Answers only from the business's data, claims checked before sending, tools scoped to the conversation, prompt-injection evals, per-conversation caps, kill switches per business and for the platform. | `docs/security/ai-components.md`, `docs/security/ai-act-assessment.md` |
| 22 | How do you handle card data? | Cards never reach the platform: payments run on the PSPs' pages; card numbers said or typed are masked. | `docs/security/payments.md` |
| 23 | How do you prevent telephony fraud? | Transfers only to the business's own numbers, premium and foreign ranges refused, concurrency caps, spend alerts and a toll-fraud playbook. | `docs/operations/runbooks/irsf-toll-fraud.md` |
| 24 | How do you report vulnerabilities? | security.txt and a disclosure policy; reports are acknowledged within 2 business days and critical fixes released within 7 days. | `SECURITY.md` |

## Resilience and incidents

| # | Question | Answer | Evidence |
| --- | --- | --- | --- |
| 25 | What are your RPO and RTO? | Internally RPO 5 minutes (point-in-time recovery) and 24 hours for the loss of the hosting account, RTO 2 hours; the SLA draft commits to RPO 15 minutes and RTO 4 hours. | `docs/operations/backup-restore.md`, `docs/legal/drafts/sla.md` |
| 26 | Are backups tested? | A nightly automated restore of a seeded database and a weekly one of production's newest backup, with integrity checks and timings; a timed full restore every quarter, recorded (the first is planned with the launch setup). | `docs/operations/restore-test-report.md` |
| 27 | Are backups immutable? | The off-site bucket is set up at a separate provider and account with Object Lock in compliance mode (31 days) and deleted versions kept 400 days, so no application or deploy key can destroy a backup within the retention window; the delete-denied test is recorded at setup. | `docs/operations/backup-restore.md`, `docs/operations/go-live.md` |
| 28 | What happens if the assistant is down? | Calls go to the business's own phone; chats wait for the team; the status page shows each component. | `docs/operations/runbooks/voice-outage.md`, `docs/operations/status-page.md` |
| 29 | Do you have an incident response plan? | Yes: severities, roles (lead, scribe, communicator, privacy lead), clocks (48 hours to businesses, 72 hours to the Garante, the PSP's deadline), postmortems and a yearly tabletop. | `docs/operations/incident.md`, `docs/operations/tabletop.md` |
| 30 | What availability do you commit to? | The SLA draft: 99.5% monthly for the assistant's answers, with support hours and credits; to be adopted with the terms. | `docs/legal/drafts/sla.md`, `docs/operations/slo.md` |
