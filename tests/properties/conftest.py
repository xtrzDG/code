"""
Property tests (Hypothesis). The default profile is reproducible: examples
are derived from each test, not drawn at random, and no example database is
written, so CI runs the same cases every time and a failure reproduces
locally. `HYPOTHESIS_PROFILE=explore` draws new random examples, many more
of them, to look for new failures; a failure it finds becomes an
`@example` of its test.

The storage fixtures (a throwaway Postgres) come from tests/storage.
"""

import os

from hypothesis import settings

from tests.storage.conftest import (
    connection_pool,
    database_name,
    database_url,
    migrated_template_database,
    platform_scope,
    postgres_collections,
    postgres_server,
    storage_scope,
)

__all__ = [
    "connection_pool",
    "database_name",
    "database_url",
    "migrated_template_database",
    "platform_scope",
    "postgres_collections",
    "postgres_server",
    "storage_scope",
]

settings.register_profile(
    "reproducible",
    derandomize=True,
    database=None,
    deadline=None,
    print_blob=True,
)
settings.register_profile("explore", max_examples=2_000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "reproducible"))
