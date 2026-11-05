# The data processing agreement and the legal texts

The texts and the operator's checklist are in
[`docs/legal/`](../legal/README.md); this page is how the code serves them.

## The DPA

The DPA is `docs/legal/dpa-<version>.<language>.md` in English, Russian and
Georgian. The API serves it at `GET /v1/legal/dpa/{version}?language=` (the
language, then its base language, then English), the status
`GET …/dpa` links to it in `document_url`, and the cabinet shows it before the
Accept button. The version in force is `DPA_DOCUMENT_VERSION`; a version
without a text cannot be accepted.

> **It is a template.** Before going into production the operator has a
> lawyer of their jurisdiction and of their clients' countries review it,
> fills in the fields in square brackets (company details, the
> sub-processors' processing locations, periods, backups, governing law) and
> releases changes as a new version (new files and a new
> `DPA_DOCUMENT_VERSION`), so owners accept it again.

The sub-processor table of section 8 is built from the registry in
`app/registries/legal/` (`SubprocessorRegistry`): the API serves the DPA with
the table from the registry, and `uv run python -m
scripts.render_subprocessor_table` updates the files (`--check` only
compares). Every module of `app/clients/` is either named by a sub-processor
or listed among the modules without one, with a reason; otherwise a test
fails. Adding or removing a sub-processor is recorded in the registry with
the date it takes effect and an announcement date at least 30 days earlier;
the worker's daily job `send_subprocessor_notices` writes to the owners of
every business 30 days ahead and records the notice in the audit log.

## Terms, privacy and cookies

The terms of use, the privacy policy and the cookie statement (functional
cookies only) live in the same folder: `terms|privacy|cookies-<date>.<language>.md`.
The file with the latest date not after today is in force; a file with a
future date is served as `upcoming_version`. At the code step the cabinet
says "By continuing you accept…" with links to both texts, and the sign-in
stores the version shown in the user's `accepted_terms_version`. The fields
in square brackets block the launch in [`docs/LAUNCH.md`](../LAUNCH.md), and
`LEGAL_TEXTS_FINAL` keeps the public pages marked as drafts until they are
filled ([`environment.md`](environment.md)).
