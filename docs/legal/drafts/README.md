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
API serves.

Sections 8 (sub-processors) and 9 (security measures) are generated from the
registries in `app/registries/legal/`, which hold no Italian today; the drafts
keep their markers with a placeholder.

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
