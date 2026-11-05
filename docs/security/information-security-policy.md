# Information security policy

Version 1, 2026-11-03. The platform's policy for protecting the
information it holds for itself and for the businesses that use it: what
everyone on the team must do, who owns what, and where each rule is
carried out. It is short on purpose: each section points to the document
or code that implements it. Every person with access reads it before their
first access and acknowledges it (below); it is reviewed at least once a
year and after every SEV1 incident.

Reviewed: 2026-11-03. Owner: the founder, as **security owner** (until a
named person takes over in `docs/operations/contacts.md`). Approved by:
[the founder's name, date of signature].

`tests/legal/test_information_security_policy.py` keeps it reviewed within
a year, its paths real and its acknowledgment table in place.

## 1. Scope and objectives

Everything the platform runs and everyone who can reach it: the API, the
workers, the cabinet, the widget and the public pages; the database,
backups and object storage; provider consoles (`docs/operations/vendor-register.md`);
source code, CI and the release path; the team's laptops and accounts.

Objectives: no business ever sees another's data; customers' data stays
in the EU unless a listed safeguard applies; a lost database is restored
within the targets of `docs/operations/backup-restore.md`; incidents are
noticed and handled within the clocks of `docs/operations/incident.md`;
the controls are proven by tests and records, not by belief.

## 2. Roles

| Role | Who | Responsible for |
| --- | --- | --- |
| Security owner | the founder | this policy, the risk register, exceptions, the yearly reviews |
| Privacy lead | the founder unless `docs/operations/contacts.md` names another | records of processing, DPIA, data subjects' requests, breach notifications |
| Incident lead | the person on call (`docs/operations/on-call.md`) | running an incident until it is closed |
| Every team member | everyone with access | following this policy, reporting anything suspicious at once |

## 3. Risk management

Risks are listed with likelihood, impact, owner and treatment in
`docs/security/risk-register.md`, reviewed at least yearly and whenever a
new channel, provider or kind of data arrives. The technical threats and
their mitigations are in `docs/security/threat-model.md`; the data
protection risks in `docs/security/dpia.md`.

## 4. Asset inventory

The inventory is kept as code and documents, each checked by tests:
entry points (`docs/security/entry-points.json`), secrets
(`docs/security/secrets-inventory.md`), data categories and transfers
(`docs/security/data-classification.md`), vendors
(`docs/operations/vendor-register.md`), service dependencies
(`docs/operations/dependency-map.md`), sub-processors
(`app/registries/legal/`). Laptops used for the platform are listed in the
password manager's vault with their owner and disk encryption state.

## 5. Access control

- Least privilege: the smallest role that is enough
  (`docs/security/permission-matrix.md`); production data only through the
  cabinet and the admin console, never by copying it to a laptop.
- No shared accounts. Every console that offers it has a second factor;
  platform admins sign in with a passkey in production.
- Access is reviewed every quarter (`docs/security/access-review.md`) and
  removed within 24 hours of leaving (`docs/operations/offboarding.md`).
- Support looks into a business's cabinet only with a recorded reason,
  read-only by default, and the business sees it in its audit log.

## 6. Cryptography and secrets

Data in transit uses TLS; secrets, channel credentials and recordings are
encrypted at rest (`app/utilities/security/`); backups are encrypted with
age to keys never held by a server. Secrets live only in the hosting
provider's secret store and the vault, have an owner and a rotation
period (`docs/security/secrets-inventory.md`,
`docs/operations/runbooks/secret-rotation.md`) and are never committed,
logged or pasted into chats.

## 7. Secure development and change

Every change goes through a pull request with the risk class of
`docs/security/change-risk.md` and the gates of `SECURITY.md` (tests,
types, static analysis, dependency and secret scanning, image scanning,
signed images). Production deploys only reviewed commits of `release`
(`docs/operations/deploys.md`). New dependencies are reviewed
(`.github/dependency-review-config.yml`).

## 8. Suppliers

A vendor that receives personal data is assessed before it joins, signs a
DPA, is listed with its location and safeguard
(`docs/operations/vendor-register.md`) and, as a sub-processor, announced
to businesses 30 days ahead (DPA section 8).

## 9. Logging, monitoring and incidents

Security events and audit entries are recorded as described in
`docs/security/log-inventory.md`; alerts page the person on call
(`docs/operations/observability.md`). Incidents follow
`docs/operations/incident.md`; a yearly tabletop exercise
(`docs/operations/tabletop.md`) tests the plan.

## 10. Continuity

Backups, restore drills and the recovery targets:
`docs/operations/backup-restore.md`, with the quarterly evidence in
`docs/operations/restore-test-report.md`. Service objectives:
`docs/operations/slo.md`.

## 11. People

- Training before the first access and yearly
  (`docs/security/ai-literacy.md`): the assistant's limits, prompt
  injection, social engineering, data protection, incidents.
- Laptops: full-disk encryption, screen lock, automatic updates, a
  password manager, no customer data stored locally.
- AI tools: customers' or businesses' data never goes into a personal AI
  tool or any service outside the vendor register.
- Report phishing, a lost device or a suspected leak at once in the team
  chat and to the person on call.

## 12. Compliance

Which laws apply and why is kept in `docs/security/regulatory-register.md`
and reviewed yearly; the AI Act record is
`docs/security/ai-act-assessment.md`; GDPR records are
`docs/legal/records-of-processing.md` and `docs/security/dpia.md`.

## 13. Exceptions

An exception to this policy is written down (what, why, until when, who
accepted the risk) in the risk register and approved by the security
owner. A gate exception in code needs its reason in `SECURITY.md` or the
file itself.

## Acknowledgments

Each person confirms they read this version and will follow it. Keep a
row per person and version; a new version is acknowledged again.

| Person | Role | Version | Date | How confirmed |
| --- | --- | --- | --- | --- |
| [the founder] | security owner | 1 | [date of signature] | signed copy in the company drive |
