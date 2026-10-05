from app.schemas.exceptions.application_errors import ExternalServiceError


class UndeclaredLookupFieldError(LookupError):
    """
    A storage query used a field its collection does not declare as a lookup
    field of that kind (see `app/utilities/storage/document_lookup_fields.py`).

    A programming error, not a business error: the field has no index, so
    the query would read the whole table. Declare the field and index it in
    a migration, or query by a declared one.
    """


class UnreadableStoredDocumentError(ValueError):
    """
    A stored document is not a JSON object, or its `schema_version` is not
    a positive whole number, so no upcaster can tell what shape it has.

    A data error, not a business error: the row was written by something
    other than the document collections (a manual edit, a broken import).
    """


class UnscopedStorageAccessError(RuntimeError):
    """
    Code touched a tenant collection without a storage scope (fail-closed,
    see `StorageScopeContract`).

    A programming error, not a business error: a request or job for one
    business must run inside `scoped_to_business(...)` (operators and the
    job runner do that from the business id of their input), and
    platform-level code must say so with `platform_wide()`.
    """


class MigrationLockTimeoutError(ExternalServiceError):
    """
    A migration file waited longer than the runner's `lock_timeout` for a
    lock (or lost a deadlock) and was rolled back, so it never queued in
    front of the live release's writes. The runner tries it again after a
    pause; nothing of the failed try is kept.
    """
