# Security and governance documents

What each document answers, and the test that keeps it true. The reporting
policy and the gates of the code are in `SECURITY.md`.

| Document | Answers | Kept true by |
| --- | --- | --- |
| `docs/security/threat-model.md` | the trust boundaries and, threat by threat, the mitigation with its code and tests | `tests/legal/test_security_documents.py` |
| `docs/security/runtime-protections.md` | what the running API, worker and cabinet refuse and limit at the platform's edge (configuration, sign-in, the API, the cabinet, monitoring), each with its code and test | `tests/legal/test_operations_documents.py` |
| `docs/security/product-protections.md` | the same for the AI agent, calls, bookings, payments and customers' data | `tests/legal/test_operations_documents.py` |
| `docs/security/dpia.md` | the platform's data protection impact assessment | |
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

Operations: on call and severity (`docs/operations/on-call.md`), contacts
(`docs/operations/contacts.md`), offboarding (`docs/operations/offboarding.md`),
the vendor register (`docs/operations/vendor-register.md`), the dependency
map (`docs/operations/dependency-map.md`), maintenance and postmortems
(`docs/operations/maintenance.md`) and the yearly tabletop
(`docs/operations/tabletop.md`), checked by
`tests/legal/test_operations_documents.py`.
