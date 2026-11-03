# Security and governance documents

What each document answers, and the test that keeps it true. The reporting
policy and the gates of the code are in `SECURITY.md`.

| Document | Answers | Kept true by |
| --- | --- | --- |
| `docs/security/threat-model.md` | the trust boundaries and, threat by threat, the mitigation with its code and tests | `tests/legal/test_security_documents.py` |
| `docs/security/runtime-protections.md` | what the running API, worker and cabinet refuse and limit at the platform's edge (configuration, sign-in, the API, the cabinet, monitoring), each with its code and test | `tests/legal/test_operations_documents.py` |
| `docs/security/product-protections.md` | the same for the AI agent, calls, bookings, payments and customers' data | `tests/legal/test_operations_documents.py` |
| `docs/security/dpia.md` | the platform's data protection impact assessment, no-show history and profiling included, each risk mapped to checklist items | `tests/legal/test_dpia.py` |
| `docs/security/entry-points.json` | every HTTP route, webhook, worker job and command with its access class (generated) | `tests/platform/test_entry_point_inventory.py` |
| `docs/security/permission-matrix.md` | what each role may do (generated) | `tests/platform/test_entry_point_inventory.py` |
| `docs/security/secrets-inventory.md` | every secret: purpose, owner, store, rotation | `tests/legal/test_secrets_inventory.py` |
| `docs/security/data-classification.md` | data categories, transfers outside the EEA, retention and how the purge is watched | `tests/legal/test_data_classification.py` |
| `docs/security/payments.md` | the payment data flows, why no card data reaches the platform, the SAQ A eligibility and the PCI responsibility matrix for businesses | `tests/legal/test_payments_document.py` |
| `docs/security/log-inventory.md` | what is logged where (loggers, security events, audit entry fields), its encoding and retention | `tests/security/test_log_inventory.py` |
| `docs/security/change-risk.md` | the risk classes of a pull request and the differential review of HIGH ones | `tests/legal/test_change_risk.py` |
| `docs/security/access-review.md` | the quarterly review of who can reach what | `tests/legal/test_security_documents.py` |
| `docs/security/readiness-checklist.json` | the launch requirements, each with its source and how to verify it | |
| `docs/legal/drafts/dpa-art28-annex.md` | which DPA clause covers each duty of Article 28(3) GDPR | `tests/legal/test_dpa_art28_annex.py` |
| `docs/security/information-security-policy.md` | the information security policy: roles, rules and where each is carried out; who acknowledged it | `tests/legal/test_information_security_policy.py` |
| `docs/security/risk-register.md` | the business risks (AI, telephony fraud, payments, privacy, security, availability, legal, people) with likelihood, impact, owner and treatment | `tests/legal/test_risk_register.py` |
| `docs/security/regulatory-register.md` | which regimes apply (NIS2, CRA, EAA, AI Act, DPO, PCI DSS, Data Act, DSA) and what would change the answer | `tests/legal/test_regulatory_register.py` |
| `docs/security/ai-act-assessment.md` | the AI Act roles, why the assistant is not high-risk, Article 5 and Article 50, the Article 50(2) marking decision | `tests/legal/test_ai_act_assessment.py` |
| `docs/security/ai-literacy.md` | the team's AI literacy and security training, and its records | `tests/legal/test_ai_literacy.py` |
| `docs/security/roadmap.md` | the certification path (SOC 2, ISO 27001) and what waits for infrastructure or a second person (KMS, separate origins, an admin origin, independent review, the contract set) | `tests/legal/test_security_roadmap.py` |
| `docs/security/security-questionnaire.md` | prepared answers for buyers' security questionnaires | `tests/legal/test_security_questionnaire.py` |
| `docs/legal/drafts/sla.md` | the SLA draft for the owner to adopt (availability, support, RPO/RTO, call fallback, credits) | `tests/legal/test_sla_draft.py` |
| `docs/legal/records-of-processing.md` | the records of processing (article 30), reviewed every six months | `tests/legal/test_records_of_processing.py` |

Operations: on call and severity (`docs/operations/on-call.md`), contacts
(`docs/operations/contacts.md`), offboarding (`docs/operations/offboarding.md`),
the vendor register with its transfer register
(`docs/operations/vendor-register.md`; `tests/legal/test_subprocessor_transfers.py`
too), the restore test reports (`docs/operations/restore-test-report.md`;
`tests/legal/test_restore_test_report.py`), the dependency
map (`docs/operations/dependency-map.md`), maintenance and postmortems
(`docs/operations/maintenance.md`) and the yearly tabletop
(`docs/operations/tabletop.md`), checked by
`tests/legal/test_operations_documents.py`.
