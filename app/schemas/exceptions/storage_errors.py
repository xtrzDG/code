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
