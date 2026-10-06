"""The game days run on the throwaway Postgres of the storage tests."""

from tests.storage.conftest import (
    migrated_template_database,
    postgres_server,
)

__all__ = ["migrated_template_database", "postgres_server"]
