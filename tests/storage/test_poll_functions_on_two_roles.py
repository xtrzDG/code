"""
The widget poll's database functions follow the two roles of 1200: the
request rate limits (`workshop.count_request_within_limits`, 1135, and the
lease `workshop.lease_requests_within_limit`, 1215) run on the platform
pool, and only workshop_platform may call them; the poll's one-statement
read (`workshop.read_widget_poll`, 1216) runs in a business's scope on the
tenant pool, where the tenant role's row-level security binds it, and the
two groups may call it, nobody else (PUBLIC holds none of the three).
"""

import psycopg
import pytest
from psycopg import errors
from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.rate_limits.postgres_rate_limit_bucket_adapter import (
    PostgresRateLimitBucketAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.constrained_integers import (
    RateLimitLeaseSize,
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import locate_window
from tests.storage.postgres_roles import (
    PLATFORM_GROUP,
    TENANT_GROUP,
    RoleDatabase,
)
from tests.storage.postgres_server import ThrowawayPostgresServer

WINDOW = locate_window(Microseconds(1_789_999_985_000_000), RateWindowSeconds(60))
COUNTER = RateLimitCounter(
    key=RateLimitKey("widget-poll:business:biz_roles"),
    limit=RequestsPerWindow(10),
    lease_size=RateLimitLeaseSize(2),
)
FUNCTIONS: dict[str, str] = {
    "count_request_within_limits": (
        "workshop.count_request_within_limits("
        "text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint)"
    ),
    "lease_requests_within_limit": (
        "workshop.lease_requests_within_limit("
        "text, integer, integer, integer, bigint, bigint, bigint, bigint, bigint)"
    ),
    "read_widget_poll": (
        "workshop.read_widget_poll(text, text, text, text, integer, text)"
    ),
}


def test_the_platform_role_counts_and_leases_and_the_tenant_role_may_not(
    role_urls: RoleDatabase,
) -> None:
    platform = PostgresConnectionPoolClient(role_urls.platform_url, max_size=1)
    tenant = PostgresConnectionPoolClient(role_urls.tenant_url, max_size=1)
    try:
        on_platform = PostgresRateLimitBucketAdapter(platform)
        assert (
            int(on_platform.lease_within(COUNTER, RateLimitLeaseSize(2), WINDOW)) == 2
        )
        assert on_platform.count_if_within([COUNTER], WINDOW) is None

        on_tenant = PostgresRateLimitBucketAdapter(tenant)
        with pytest.raises(ExternalServiceError) as leased:
            on_tenant.lease_within(COUNTER, RateLimitLeaseSize(2), WINDOW)
        with pytest.raises(ExternalServiceError) as counted:
            on_tenant.count_if_within([COUNTER], WINDOW)
        stored = on_platform.read_counts(COUNTER.key, WINDOW)
    finally:
        platform.close()
        tenant.close()

    assert isinstance(leased.value.__cause__, errors.InsufficientPrivilege)
    assert isinstance(counted.value.__cause__, errors.InsufficientPrivilege)
    # The lease's two units and the request counted one by one.
    assert int(stored.current_count) == 3


def test_only_the_groups_named_may_call_the_poll_functions(
    postgres_server: ThrowawayPostgresServer, database_name: str
) -> None:
    allowed: dict[str, set[str]] = {
        "count_request_within_limits": {PLATFORM_GROUP},
        "lease_requests_within_limit": {PLATFORM_GROUP},
        "read_widget_poll": {PLATFORM_GROUP, TENANT_GROUP},
    }
    with postgres_server.admin_connection(database_name) as admin:
        found: dict[str, set[str]] = {
            name: {
                group
                for group in (TENANT_GROUP, PLATFORM_GROUP)
                if privilege_of(admin, group, signature)
            }
            for name, signature in FUNCTIONS.items()
        }
        public: list[bool] = [
            privilege_of(admin, "public", signature) for signature in FUNCTIONS.values()
        ]

    assert found == allowed
    assert public == [False, False, False]


def privilege_of(
    connection: psycopg.Connection[TupleRow], role: str, signature: str
) -> bool:
    """Whether `role` may execute the function (PUBLIC: granted to it itself)."""

    if role == "public":
        row = connection.execute(
            "select exists (select 1 from pg_proc p,"
            " aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) acl"
            " where p.oid = %s::regprocedure and acl.grantee = 0"
            " and acl.privilege_type = 'EXECUTE')",
            (signature,),
        ).fetchone()
    else:
        row = connection.execute(
            "select has_function_privilege(%s, %s, 'execute')", (role, signature)
        ).fetchone()
    return row is not None and row[0] is True
