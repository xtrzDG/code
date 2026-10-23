# 0009. Documents evolve by expand and contract; enum values ship a release ahead

- Status: Accepted
- Date: 2026-10-22

## Context

Tenant data is stored as JSONB documents validated by strict pydantic
models (ADR 0001, `extra="forbid"`). Two releases run side by side during
every deploy, and after a rollback the older one reads what the newer one
wrote. A renamed field, a field made required, a changed type or a new enum
value written by the new release makes the old one fail to load the whole
document: a conversation, a booking or a business suddenly cannot be read
by half the instances. Such failures appear only under a mixed deploy, so
ordinary tests never see them.

## Decision

- **Versioned documents and tolerant reads.** Every stored document carries
  its `schema_version`. Documents stay strict wherever they are built and
  written; only the storage read path (`PersistedDocumentCodec`) ignores
  unknown fields and runs older versions through the pure upcasters of
  `app/adapters/storage/document_upgrades.py`. Inputs and DTOs are never
  relaxed to make old data load.
- **Expand, backfill, require.** A shape changes over releases: add the field
  as optional and bump the version (with a golden fixture,
  `tests/storage/golden/<collection>/v<N>.json`); fill old rows with an
  upcaster and the post-release data task (`migrate-documents`); make it
  required only in a later release. Never rename, remove or retype a field in
  one release.
- **The enum rule.** A release writes only enum values the release before it
  already reads. A new value is added behind a closed release gate
  (`app/utilities/storage/release_gates.py`), which storage refuses to write;
  the next release opens the gate, the one after deletes it. A field that is
  its document's key (alert codes) is exempt, because a release reads only
  the keys it knows.
- **Enforcement.** `tests/architecture_policy/test_document_evolution.py`
  fails on a shape change without a version bump or a golden fixture, on a
  fixture that no longer loads and on an upcaster that leaves the old shape
  behind; `test_enum_values_are_known_one_release_ahead.py` compares every
  stored enum with the snapshot of the last release
  (`tests/storage/release_enums.json`) and fails on a value no closed gate
  covers. An N-1 test reads the current documents with the previous
  release's code.

## Consequences

- Deploys and rollbacks never strand documents the other release cannot
  read, and the checks catch the mistake in the pull request rather than
  under a mixed deploy.
- Changes take two or three releases, each with its own pull request, and the
  operator records the enum snapshot when a release reaches production
  (`docs/operations/deploys.md`). A few audited exceptions to the enum rule
  are listed there with the reason the previous release survives them.
- Golden fixtures are history: never edited, deleted only with their
  upcaster once `migrate-documents` rewrote every row; the test suite carries
  the cost of keeping them loadable.
