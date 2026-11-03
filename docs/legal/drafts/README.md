# Drafts of legal texts (needs_review)

The cabinet speaks English and Italian (`CABINET_LANGUAGES`). The legal texts
owners accept are published in English only; the files here are **unreviewed
translation drafts** for the other cabinet language:

| File | Translates | Status |
| --- | --- | --- |
| `dpa-2026-10-06.it.md` | `../dpa-2026-10-06.en.md` | needs_review |

They are not served and cannot be accepted: the API reads only
`docs/legal/*.md`, so an Italian owner reads the English DPA until the draft
is published. They are not in `published.json` either, so they can be edited
freely until then. `tests/legal/test_legal_drafts.py` keeps every draft
marked `needs_review`, numbered like its English text and outside what the
API serves, and checks that the next DPA version closes the gaps of
`dpa-art28-annex.md` it was drafted for.

`dpa-2026-11-03.en.md` is the **next version** of the DPA in English, not a
translation: clause 2.3 adds Article 28(3)(a)'s duty to tell the Client of
a legal requirement to process otherwise, 13.3 describes closing and
deleting a business in the cabinet with its certificate, 7.2 and section 8
name every sub-processor's transfer mechanism, and 1.4 names Italian law.
It is a draft for the lawyer (needs_review), not served and not in
`published.json`. To put it in force: the lawyer reviews it and fills its
fields; move it to `docs/legal/` (`git mv`), translate it into Italian
here, run `uv run python -m scripts.render_subprocessor_table` and
`uv run python -m scripts.publish_legal_texts`, set the default
`DPA_DOCUMENT_VERSION` in `compliance_settings_section.py` to `2026-11-03`
(or a later date of the reviewed text, renaming the file) and rebuild;
owners are then asked to accept it within 30 days.

Sections 8 (sub-processors) and 9 (security measures) are generated from the
registries in `app/registries/legal/`, which hold no Italian today; the drafts
keep their markers with a placeholder.

`dpa-art28-annex.md` is not a translation: it maps the DPA in force to each
duty of Article 28(3) GDPR for a reviewing lawyer, an auditor or a
business's DPO, and collects what the next DPA version should fix
(`tests/legal/test_dpa_art28_annex.py`).

`data-act-switching.md` is not a translation either: it describes the full
export's archive (format 2: every file and its meaning), what happens after
the end, and the switching clauses (notice, transitional and retrieval
periods, charges) the next terms version must carry under the Data Act, for
the lawyer and for the switching information published before contracting.

## Publishing a draft

1. A lawyer who is a native speaker of the language reviews the draft
   against the English text of the same version, fills the fields in square
   brackets like the published text, and removes the "Draft
   (needs_review)" notice.
2. Add the language to the sub-processor entries (`subprocessor_entries_*.py`)
   and the security measures (`security_measures_*.py`), so the generated
   sections have their text.
3. Move the file to `docs/legal/` under the same name, run
   `uv run python -m scripts.render_subprocessor_table` and
   `uv run python -m scripts.publish_legal_texts` (docs/legal/README.md).

A draft of a version that is no longer in force is not published; translate
the version in force instead.
