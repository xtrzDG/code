# Legal documents

`dpa-<version>.<language>.md` is the data processing agreement (DPA) that
business owners accept in the cabinet (Settings → Data protection). The API
serves it at `GET /v1/legal/dpa/<version>?language=<tag>` (requested language,
then its base language, then English) and links it from
`GET /v1/businesses/{id}/dpa` as `document_url`. The version in force is
`DPA_DOCUMENT_VERSION` (default `2026-10-01`); a version without a text cannot be
accepted.

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
