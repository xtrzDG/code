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
