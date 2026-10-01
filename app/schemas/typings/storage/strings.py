"""Keep abc order."""

from base_typed_string import BaseTypedString


class SchemaMigrationSql(BaseTypedString):
    """SQL text of one migration file, executed as one transaction."""


# Keep abc order for all non example types, if possible.
