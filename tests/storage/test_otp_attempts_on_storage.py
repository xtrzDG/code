"""
The login code challenge's attempt counter and consumption are atomic on
every storage: parallel failed checks each get their own count up to the
limit and no further, and one consumption wins.
"""

import threading
from collections.abc import Callable

from typed_time_provider import Microseconds

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.user_repositories import OtpChallengeRepository
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.users.constrained_integers import OtpAttemptCount
from app.schemas.typings.users.strings import OtpCodeHash
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.concurrency_limits import POOL_SIZE
from tests.storage.conftest import CollectionFactory, PostgresCollectionFactory
from tests.storage.storage_testing import build_ticking_wall_clock

PARALLEL_CHECKS: int = 40
MAX_FAILED_ATTEMPTS: OtpAttemptCount = OtpAttemptCount(5)
NOW: Microseconds = Microseconds(1_790_000_000_000_000)


def build_challenge() -> OtpChallengeDocument:
    return OtpChallengeDocument(
        login_method=LoginMethod.PHONE,
        phone_number=E164PhoneNumber("+995555123456"),
        delivery_channel=OtpDeliveryChannel.SMS,
        locale=LanguageTag("ka"),
        code_hash=OtpCodeHash("hash"),
        expires_at=Microseconds(int(NOW) + 600_000_000),
        created_at=NOW,
        updated_at=NOW,
    )


def run_in_parallel[Result](count: int, action: Callable[[], Result]) -> list[Result]:
    results: list[Result] = []
    errors: list[BaseException] = []
    lock = threading.Lock()
    start = threading.Barrier(count)

    def run() -> None:
        start.wait()
        try:
            result = action()
        except BaseException as error:  # noqa: BLE001 - reported below
            with lock:
                errors.append(error)
            return
        with lock:
            results.append(result)

    threads = [threading.Thread(target=run) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    return results


def check_attempt_race(repo: OtpChallengeRepository) -> None:
    challenge = build_challenge()
    repo.save(challenge)

    counts = run_in_parallel(
        PARALLEL_CHECKS,
        lambda: repo.register_failed_attempt(challenge.id, MAX_FAILED_ATTEMPTS, NOW),
    )

    assert sorted(int(count) for count in counts if count is not None) == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert counts.count(None) == PARALLEL_CHECKS - 5
    stored = repo.get(challenge.id)
    assert stored is not None
    assert stored.failed_attempts == 5


def check_consumption_race(repo: OtpChallengeRepository) -> None:
    challenge = build_challenge()
    repo.save(challenge)

    consumed = run_in_parallel(8, lambda: repo.consume(challenge.id, NOW))

    assert len([result for result in consumed if result is not None]) == 1
    # A consumed challenge takes no more attempts.
    assert repo.register_failed_attempt(challenge.id, MAX_FAILED_ATTEMPTS, NOW) is None


def test_attempts_and_consumption_on_every_storage(
    collections: CollectionFactory,
) -> None:
    repo = OtpChallengeRepository(collections(OtpChallengeDocument, "otp_challenges"))
    challenge = build_challenge()
    repo.save(challenge)

    first = repo.register_failed_attempt(challenge.id, MAX_FAILED_ATTEMPTS, NOW)
    consumed = repo.consume(challenge.id, NOW)

    assert first == 1
    assert consumed is not None
    assert consumed.is_consumed
    assert consumed.failed_attempts == 1
    assert repo.consume(challenge.id, NOW) is None
    missing = build_challenge()
    assert repo.register_failed_attempt(missing.id, MAX_FAILED_ATTEMPTS, NOW) is None
    assert repo.consume(missing.id, NOW) is None


def test_parallel_checks_on_every_storage(collections: CollectionFactory) -> None:
    repo = OtpChallengeRepository(collections(OtpChallengeDocument, "otp_challenges"))

    check_attempt_race(repo)
    check_consumption_race(repo)


def test_parallel_failed_attempts_on_postgres_through_a_small_pool(
    database_url: DatabaseUrl,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=POOL_SIZE,
        acquire_timeout_seconds=30,
    )
    try:
        repo = OtpChallengeRepository(
            PostgresCollectionFactory(
                connection_pool=connection_pool,
                storage_scope=StorageScopeContext(),
                wall_clock=build_ticking_wall_clock(),
            )(OtpChallengeDocument, "otp_challenges")
        )

        check_attempt_race(repo)
        check_consumption_race(repo)
    finally:
        connection_pool.close()
