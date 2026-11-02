# Annex: Article 28(3) GDPR mapping of the Data Processing Agreement

Draft (needs_review). Applies to version 2026-10-06 of the Data Processing
Agreement (`docs/legal/dpa-2026-10-06.en.md`). Not served and not part of
what owners accept: it is the working map a reviewing lawyer, an auditor or
a business's DPO uses to check the agreement duty by duty, and the place
the next DPA version's gaps are collected. `tests/legal/test_dpa_art28_annex.py`
checks that every duty of Article 28(3)(a) to (h) has a row, that every
clause it cites exists in the DPA version it names, and that every code or
test path exists.

## Duties of Article 28(3)

| Duty | Article 28(3) | DPA clauses | How the service meets it | Evidence |
| --- | --- | --- | --- | --- |
| (a) | Processes only on documented instructions, including for transfers to third countries; informs the controller of a legal requirement to process otherwise (not yet in the text: see the gaps) | 2.3, 6.1, 7.2 | The business's settings in the cabinet are its instructions; data reach a sub-processor only for the purposes the registry names, and production refuses to start otherwise | `app/registries/legal/processor_use_catalog.py`, `app/utilities/legal/processor_coverage.py`, `tests/legal/test_processor_uses.py` |
| (b) | Persons authorised to process are bound by confidentiality | 6.1 | Contracts of the platform team carry a confidentiality clause; access is least-privilege and reviewed each quarter | `docs/security/access-review.md`, `docs/operations/offboarding.md` |
| (c) | Takes the measures of Article 32 | 6.1, 9.1 | Section 9 is generated from the security measure registry, each measure naming its code | `app/registries/legal/security_measures_data.py`, `tests/legal/test_security_measures.py`, `docs/security/threat-model.md` |
| (d) | Engages another processor only with prior authorisation and under the same obligations (Article 28(2) and (4)) | 8.1, 8.2, 8.3 | The sub-processor list is kept in code; an addition is announced to every owner 30 days ahead and the business may object or leave | `app/registries/legal/subprocessor_registry.py`, `app/use_cases/legal/send_subprocessor_notices_use_case.py`, `tests/legal/test_subprocessor_notices.py`, `docs/operations/vendor-register.md` |
| (e) | Assists the controller with data subjects' requests | 5.3, 6.1, 11.1, 11.2, 11.3 | The owner finds a customer, exports everything about them and erases it from the cabinet; every export and erasure is audited; erasure reaches the sub-processors' copies | `app/use_cases/compliance/export_contact_data_use_case.py`, `app/use_cases/compliance/delete_contact_data_use_case.py`, `app/use_cases/compliance/erase_processor_copies_use_case.py`, `tests/compliance/test_contact_data_rights.py` |
| (f) | Assists with Articles 32 to 36: security, breach notification, DPIA and prior consultation | 6.1, 9.1, 12.1, 12.2 | Breach notices to every owner within 48 hours through the incident tool; the DPIA support pack for businesses (help article "DPIA support") | `docs/operations/incident.md`, `docs/operations/runbooks/data-breach.md`, `docs/help/en/dpia-support.md`, `docs/help/it/dpia-support.md` |
| (g) | Deletes or returns all personal data at the end of the services, and deletes existing copies | 4.1, 11.2, 13.3 | The owner exports the whole business, then closes it; 30 days later the business is deleted in stages, the sub-processors' copies with it, and a deletion certificate is issued; backups age out (30 daily, 12 monthly copies) and a restore re-applies the deletions | `app/use_cases/businesses/closure/close_business_use_case.py`, `app/use_cases/businesses/deletion/delete_business_use_case.py`, `tests/business_closures/test_business_deletion_journey.py`, `tests/business_closures/test_ledger_reapplied.py` |
| (h) | Makes available all information to demonstrate compliance and allows audits | 6.1, 10.1 | The audit log in the cabinet, this annex, the security measures, the sub-processor list and the vendor attestations; an audit once a year on notice | `app/use_cases/compliance/list_audit_log_use_case.py`, `tests/compliance/test_audit_log.py` |
| (h), second subparagraph | Tells the controller at once when, in its opinion, an instruction infringes data protection law | 2.4 | Support raises it with the owner in writing (`docs/operations/contacts.md`) | the support record |

## Other paragraphs of Article 28

| Paragraph | DPA clauses | Notes |
| --- | --- | --- |
| 28(1) sufficient guarantees | 9.1, 10.1 | The security measures and the vendor register |
| 28(9) in writing, including electronic form | 15.1, 15.2 | Acceptance records version, account, time and IP address (`app/use_cases/compliance/accept_dpa_use_case.py`, `tests/compliance/test_dpa.py`) |
| 28(10) a processor deciding purposes becomes controller | 2.3 | The platform does not use the businesses' data for its own purposes or for training |

## Gaps for the next DPA version

The first one leaves part of a duty without a clause; the others are text
that lags the service or still has open fields. Collect them for the next
version and the lawyer's review:

- (a) also asks the processor to tell the controller, before processing, of
  a Union or Member State law that requires processing outside the
  instructions, unless that law forbids telling. Neither 2.3 nor 6.1 says
  so: add it to 2.3.
- 13.3 says deletion after the end happens "through support (the cabinet
  does not offer this yet)": the cabinet now offers closing and deleting a
  business with a deletion certificate (row (g)).
- 7.2 and section 8 still carry "[to be confirmed]" locations and transfer
  mechanisms; the vendor register holds the facts to fill them.
- 1.2, 10.1, 11.3, 12.1, 13.3, 14.1 and 8.3 have fields in square brackets
  (the operator's identity, notice periods, governing law).
- 3.3 leaves "[Additional safeguards for special categories, if any]": the
  DPIA support pack names the booking notes that may hold health data.
- (b) relies on the team's employment and contractor agreements; keep a copy
  of each signed confidentiality clause with the offboarding records.
