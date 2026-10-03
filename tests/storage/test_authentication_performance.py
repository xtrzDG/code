"""
Sign-in cost does not grow with the session table: authenticating a bearer
token takes well under 5 ms with 50,000 sessions stored (perf marker; run
alone with `uv run pytest -m perf`).
"""

import statistics
import time
from collections.abc import Generator

import pytest
from typed_time_provider import Microseconds

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.domain.users import UserSessionDocument
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.users.authenticate_user_use_case import AuthenticateUserUseCase
from app.utilities.security.access_tokens import (
    generate_access_token,
    hash_access_token,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_owner
from tests.storage.hot_path_repositories import HotPathRepositories
from tests.storage.hot_path_seeding import analyze, insert_session_rows
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import FIXED_NANOSECONDS, build_fixed_wall_clock

SESSION_COUNT: int = 50_000
MEASURED_RUNS: int = 200
WARM_UP_RUNS: int = 20
BUDGET_MILLISECONDS: float = 5.0
NOW: int = FIXED_NANOSECONDS // 1_000

pytestmark = pytest.mark.perf


@pytest.fixture
def big_session_table_url(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
) -> Generator[DatabaseUrl]:
    database_name = postgres_server.create_database(
        template_name=migrated_template_database
    )
    database_url = postgres_server.app_database_url(database_name)
    connection_pool = PostgresConnectionPoolClient(database_url, max_size=1)
    try:
        insert_session_rows(connection_pool, count=SESSION_COUNT, expires_at=NOW)
        analyze(connection_pool)
        connection_pool.close()
        yield database_url
    finally:
        connection_pool.close()
        postgres_server.drop_database(database_name)


def test_authenticate_stays_under_5_ms_with_50k_sessions(
    big_session_table_url: DatabaseUrl,
) -> None:
    connection_pool = PostgresConnectionPoolClient(big_session_table_url, max_size=2)
    repositories = HotPathRepositories(connection_pool, StorageScopeContext())
    user = build_owner(COUNTRY_SAMPLES[0])
    repositories.users.save(user)
    token = generate_access_token()
    repositories.sessions.save(
        UserSessionDocument(
            user_id=user.id,
            token_hash=hash_access_token(token),
            expires_at=Microseconds(NOW + 3_600_000_000),
        )
    )
    authenticate = AuthenticateUserUseCase(
        user_session_repo=repositories.sessions,
        user_repo=repositories.users,
        wall_clock=build_fixed_wall_clock(),
    )
    durations: list[float] = []
    try:
        for run in range(WARM_UP_RUNS + MEASURED_RUNS):
            started: float = time.perf_counter()
            user_id: UserId = authenticate.run(token)
            if run >= WARM_UP_RUNS:
                durations.append((time.perf_counter() - started) * 1000)
            assert user_id == user.id
    finally:
        connection_pool.close()

    median: float = statistics.median(durations)
    assert median < BUDGET_MILLISECONDS, (
        f"authenticate took {median:.2f} ms (median of {MEASURED_RUNS}) "
        f"with {SESSION_COUNT} sessions"
    )
