from enum import StrEnum


class DataTaskKind(StrEnum):
    """
    What a post-deploy data task does to the rows written before a release.

    MIGRATE_DOCUMENTS rewrites a collection's documents of older schema
    versions in the current shape (`workshop migrate-documents`).
    BACKFILL_LOOKUP fills a trigger-kept lookup column of the rows written
    before the column existed (`workshop backfill-lookup`).
    """

    MIGRATE_DOCUMENTS = "migrate_documents"
    BACKFILL_LOOKUP = "backfill_lookup"


class DataTaskStatus(StrEnum):
    """
    Where a post-deploy data task stands.

    PENDING: not started for its current target (a new release, a new
    column), or waiting for the release overlap to end. RUNNING: its keyset
    walk is under way (it goes on from its stored position). DONE: every
    row was looked at and nothing failed. FAILED: the walk ended, but some
    rows could not be changed; it is walked again once a new release runs
    or a platform admin asks for it.
    """

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class IndexedList(StrEnum):
    """
    A cabinet list that pages by lookup columns which post-deploy data
    tasks fill: while one of its tasks is not done, rows written before the
    release may be missing from it, and the list says it is still indexing.
    """

    CUSTOMERS = "customers"
    KNOWLEDGE = "knowledge"
