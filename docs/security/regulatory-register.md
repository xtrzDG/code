# Regulatory applicability register

Which regimes apply to the platform, why, what that asks of it, and what
would change the answer. Prepared by the team from the facts of the
service for the lawyer's review; it is not legal advice, and every row
marked "lawyer" waits for that review. The platform is today a
micro-enterprise (fewer than 10 people, turnover under 2 million euros),
established in the EU, selling to businesses in Italy first.

Reviewed: 2026-11-03. Next review: 2027-11-03 at the latest, and at once
when headcount reaches 10 or 50, turnover passes 2 or 10 million euros, a
client app or plugin is distributed, the product adds a regulated kind of
processing, or a new country is opened. `tests/legal/test_regulatory_register.py`
fails when the review is more than a year old or a regime of the
checklist has no row.

## Register

| Regime | Applies today? | Facts and test | Decision and duties | Re-assess when | Who |
| --- | --- | --- | --- | --- | --- |
| NIS2 (Directive (EU) 2022/2555; Italy: D.Lgs. 138/2024) | no, with one open point | NIS2 covers medium and large entities of its sectors (size cap, Art. 2(1)); a SaaS for small businesses is at most a "cloud computing service" or "ICT service management" provider, both in scope only from medium size. Size-independent categories include providers of public electronic communications networks or services (Art. 2(2)(a)): the platform rents phone numbers to businesses from Twilio and Zadarma, which may make it a reseller of an electronic communications service | not in scope while a micro-enterprise; no registration on the ACN portal (the yearly window opens on 1 January). **Open point for the lawyer:** whether renting numbers to businesses is providing an electronic communications service (EECC Art. 2(4); Italian Codice delle comunicazioni elettroniche), which would also need a general authorisation from the Ministry (MIMIT) and could bring NIS2 in regardless of size | 50 people or 10 million euros of turnover; the lawyer's answer on number rental; ACN designation | the founder, lawyer |
| Cyber Resilience Act (Regulation (EU) 2024/2847) | no | the CRA covers products with digital elements placed on the market. The service is remote data processing (SaaS); the widget script is served by the platform's own servers and not distributed as a product; there is no installable app, plugin or SDK | not applicable. Keep the vulnerability disclosure policy (`SECURITY.md`) and security.txt anyway | a mobile app, desktop app, CMS plugin or SDK is published: reporting of actively exploited vulnerabilities applies from 11 September 2026, the rest from 11 December 2027 | the founder |
| European Accessibility Act (Directive (EU) 2019/882; Italy: D.Lgs. 82/2022) | likely exempt for services; statement published anyway | the booking and chat pages can be "e-commerce services" to consumers. Micro-enterprises providing services are exempt (Art. 4(5)) | the accessibility statement is published (`/accessibility`, reviewed yearly) and tenants get ready text (`docs/help/en/accessibility-statement.md`); the cabinet and customer pages target WCAG 2.2 AA | 10 people or 2 million euros of turnover | the founder |
| AI Act (Regulation (EU) 2024/1689) | yes, limited-risk | the platform is the provider, businesses are deployers; not high-risk, no prohibited practice | Art. 50 transparency, Art. 4 AI literacy: `docs/security/ai-act-assessment.md` | every release touching AI features (pull request template) | the founder, lawyer |
| GDPR: data protection officer (Art. 37) | not mandatory at launch; to confirm | the platform processes customers' conversations, calls and bookings for many businesses (processor) and its own account data (controller). Art. 37(1)(b) needs regular and systematic monitoring on a large scale as a core activity; (c) large-scale special categories. Answering enquiries is not monitoring behaviour, health details are incidental, and at launch the scale is small. The Garante's FAQ on the DPO in the private sector names call-centre and IT-service companies among those usually obliged when they process at large scale | no DPO now; the privacy lead (`docs/operations/contacts.md`) is the contact. **Decision for the lawyer:** confirm, and set the threshold (e.g. 50 businesses or 100,000 customers' conversations a month) at which an external DPO is appointed | the threshold above; profiling or monitoring features; a health-sector focus | privacy lead, lawyer |
| GDPR: records, DPIA, transfers | yes | controller and processor | `docs/legal/records-of-processing.md`, `docs/security/dpia.md`, `docs/operations/vendor-register.md` | every release adding personal data or vendors | privacy lead |
| PCI DSS | yes, smallest role | cards never reach the platform: payments run on Stripe's and Flitt's own pages | the platform's own billing: merchant SAQ A; for businesses' deposits it is a service provider whose links lead to the PSP's pages; responsibilities in `docs/security/payments.md` | an embedded card form, card data by voice, or the platform becoming merchant of record | the founder |
| Data Act (Regulation (EU) 2023/2854), switching | yes (a data processing service) | businesses must be able to switch and take their data | full export (archive format 2) and the switching clauses drafted for the next terms (`docs/legal/drafts/data-act-switching.md`) | terms review | the founder, lawyer |
| ePrivacy and Codice privacy art. 130 and 122 | yes, for the businesses' marketing and the platform's cookies | campaigns go only to consenting customers; cookies and trackers only after consent | consent ledger, quiet hours; cookie statement | outbound promotional calls or e-mail campaigns | privacy lead |
| Digital Services Act (Regulation (EU) 2022/2065) | to assess | the hosted chat and booking pages show content the businesses write; a "hosting service" would have a point of contact and a notice-and-action duty (small enterprises are spared the heavier ones) | **lawyer:** whether these pages make the platform a hosting service; if yes, a contact point and a notice form | public pages with user content beyond the business's own | the founder, lawyer |

## Decisions log

| Date | Decision | By |
| --- | --- | --- |
| 2026-11-03 | First register; NIS2 number-rental point, DPO threshold and DSA role sent to the lawyer | the founder |
