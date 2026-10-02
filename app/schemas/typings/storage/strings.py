"""Keep abc order."""

from base_typed_string import BaseTypedString


class DocumentFieldText(BaseTypedString):
    """
    A stored document field's value as text, as Postgres `document ->> field`
    gives it: a string as is, an enum as its value, a boolean as
    "true"/"false". Compared for equality in indexed lookups.
    """


class SchemaMigrationSql(BaseTypedString):
    """SQL text of one migration file, executed as one transaction."""


# Keep abc order for all non example types, if possible.
