# Legal documents

`dpa-<version>.<language>.md` is the data processing agreement (DPA) that
business owners accept in the cabinet (Settings → Data protection). The API
serves it at `GET /v1/legal/dpa/<version>?language=<tag>` (requested language,
then its base language, then English) and links it from
`GET /v1/businesses/{id}/dpa` as `document_url`. The version in force is
`DPA_DOCUMENT_VERSION` (default `2026-10-06`); a version without a text cannot be
accepted.

Hebrew and German translation drafts (not served, not accepted, marked
needs_review) wait in `drafts/` with the steps to publish them.

**These texts are templates.** Before production the operator must have them
reviewed by a lawyer for its own jurisdiction and its clients' countries, fill in
every field in square brackets (operator details, sub-processor locations,
notice periods, backups, governing law) and keep the three languages in line.
A changed text is a new version: add new files with a new date and set
`DPA_DOCUMENT_VERSION`, so owners accept it again. The texts are built into the
image and `docs/**` changes do not trigger a build on Render, so set the new
value together with a rebuild from the commit that holds the files ("Save,
rebuild, and deploy", or Manual Deploy → "Deploy latest commit"; "Save and
deploy" reuses the old build). In production the API refuses to start when the
configured version has no text in its build.

## Versions, the published record and the release check

A text owners accepted or read is never edited in place. `docs/legal/published.json`
records a fingerprint (SHA-256) of every published file; `tests/legal` fails when
a recorded file changes or disappears, and when a new file is not recorded yet.
The fingerprint leaves out the generated sub-processor table (section 8 is
served live and changes with notice, not with a new version). To change a text:

1. Copy it to a file with a new date (all three languages) and edit the copy;
   for the DPA also add a short "Changes from version …" note under the title
   and set `DPA_DOCUMENT_VERSION` (the default in
   `compliance_settings_section.py` for the next release).
2. Run `uv run python -m scripts.render_subprocessor_table`, then
   `uv run python -m scripts.publish_legal_texts` to record the new files
   (`--check` only compares).

Owners who accepted an earlier DPA version see a banner in the cabinet asking
them to accept the new one within 30 days of its date (`GET
/v1/businesses/{id}/dpa` gives `needs_reacceptance` and `acceptance_due_on`);
the assistant keeps answering meanwhile, but the go-live and publish gates
hold until an owner accepts. The business keeps the accepted version as
`dpa_version_accepted`.

`uv run python -m scripts.check_legal_texts` counts the fields in square
brackets of the texts in force (the DPA of `DPA_DOCUMENT_VERSION`, the latest
terms, privacy policy and cookie statement). CI runs it on every push: while
the repository variable `LEGAL_TEXTS_FINAL` is unset or `false` it only prints
the counts; set it to `true` once the lawyer-reviewed texts are complete, and
any field left fails the build.

## Security measures (DPA section 9)

From version 2026-10-06 on, section 9 is generated from the security measure
registry (`app/registries/legal/security_measures_*.py`) between the
`<!-- security-measures:start … -->` and `<!-- security-measures:end -->`
markers. Each measure names the code that implements it (`implemented_by`; a
test fails when a path does not exist) and the version it is first listed in
(`listed_from`, and `listed_until` when it is dropped). Unlike the
sub-processor table, the list is part of the accepted text: a version keeps
the measures of its date, and a new measure appears in the next dated
version. `scripts.render_subprocessor_table` writes both generated parts.

## Sub-processors (DPA section 8)

The section 8 table in every `dpa-*.md` is generated from the sub-processor
registry in `app/registries/legal/` (`SubprocessorRegistry`), between the
`<!-- subprocessors:start … -->` and `<!-- subprocessors:end -->` markers. The
API serves each DPA with the table rendered from the registry, and
`GET /v1/legal/subprocessors?language=` lists the same entries plus the changes
still ahead. To change the list:

1. Add or edit the entry in `subprocessor_entries_*.py` (name, purpose,
   personal data and location in English, Russian and Georgian; the
   `app/clients/` modules it covers). A removal sets `removed_on` and
   `removal_announced_on`; an addition after the original list sets
   `added_on` and `addition_announced_on`. The registry refuses a change
   announced less than 30 days ahead.
2. Run `uv run python -m scripts.render_subprocessor_table` to rewrite the
   tables in the files (`--check` only compares; the tests run it too).
3. The worker job `send_subprocessor_notices` writes to the owners of every
   business once the notice window opens (30 days before the change), records
   each notice and adds an audit entry (`subprocessor_notice`).

Every module in `app/clients/` must be named by an entry or listed in
`CLIENT_MODULES_WITHOUT_SUBPROCESSOR` with a reason; a test fails otherwise.

## Terms, privacy policy, cookie statement

`terms-<date>.<language>.md`, `privacy-<date>.<language>.md` and
`cookies-<date>.<language>.md` (English, Russian, Georgian) are served at
`GET /v1/legal/{terms|privacy|cookies}?language=<tag>[&version=<date>]`. The
version in force is the file with the latest date that is not after today
(UTC); a file with a later date is announced as `upcoming_version` and takes
effect on its date, so a new version needs no setting. The cabinet's code
step says "By continuing, you accept…" with links to the terms and the privacy
policy in force, and sign-in stores that version as the user's
`accepted_terms_version` (never lowered). The cookie statement covers the
functional cookies only; adding any analytics or marketing cookie needs a
consent banner first.

The same rule applies as for the DPA: these are templates with fields in square
brackets, listed as a launch blocker in [`docs/LAUNCH.md`](../LAUNCH.md).
