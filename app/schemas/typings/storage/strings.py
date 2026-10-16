"""Keep abc order."""

from base_typed_string import BaseTypedString


class DocumentFieldText(BaseTypedString):
    """
    A stored document field's value as text, as Postgres `document ->> field`
    gives it: a string as is, an enum as its value, a boolean as
    "true"/"false". Compared for equality in indexed lookups.
    """


class SchemaMigrationSql(BaseTypedString):
    """
    SQL text of one migration file: executed as one transaction, or
    statement by statement when the file says `-- workshop:no-transaction`.
    """


class SchemaMigrationStatement(BaseTypedString):
    """
    One SQL statement of a migration file, without its terminating
    semicolon (what a no-transaction file runs at a time).
    """


class StoredDocumentKey(BaseTypedString):
    """
    Primary key of one stored document row (`document_key`): the document's
    id as text, or the key a collection derives (a job and its period).
    """


# Keep abc order for all non example types, if possible.
