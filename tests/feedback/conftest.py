"""
The storage tests' fixtures, so the feedback repositories run on the
in-memory and on the Postgres storage (`collections`; Postgres tests are
skipped without the binaries).
"""

from tests.storage.conftest import (
    collections,
    connection_pool,
    connection_pools,
    database_name,
    database_url,
    migrated_template_database,
    postgres_collections,
    postgres_server,
    role_urls,
    storage_scope,
)

__all__ = [
    "collections",
    "connection_pool",
    "connection_pools",
    "database_name",
    "database_url",
    "migrated_template_database",
    "postgres_collections",
    "postgres_server",
    "role_urls",
    "storage_scope",
]
