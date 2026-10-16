"""Many threads saving one business: no two writes share a revision and
atomic changes are never lost.
"""

import threading
from collections.abc import Callable

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.business_repositories import BusinessRepository
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import COUNTRY_SAMPLES, build_business
from tests.storage.concurrency_limits import POOL_SIZE, THREAD_COUNT, WRITES_PER_THREAD
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.storage_testing import build_ticking_wall_clock


def adding_member(member_id: UserId) -> Callable[[BusinessDocument], None]:
    """A change that adds one staff member to the business as stored."""

    def add_member(current: BusinessDocument) -> None:
        current.members = [
            *current.members,
            BusinessMember(user_id=member_id, role=BusinessMemberRole.STAFF),
        ]

    return add_member


def test_blind_atomic_and_conditional_saves_never_share_a_revision(
    database_url: DatabaseUrl,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=POOL_SIZE,
        acquire_timeout_seconds=30,
    )
    business_repo = BusinessRepository(
        PostgresCollectionFactory(
            connection_pool=connection_pool,
            storage_scope=StorageScopeContext(),
            wall_clock=build_ticking_wall_clock(),
        )(BusinessDocument, "businesses")
    )
    business = build_business(COUNTRY_SAMPLES[0], UserId())
    business_repo.save(business)
    initial_revision = int(business.revision)
    start = threading.Barrier(THREAD_COUNT)
    write_count: list[int] = []
    added_members: list[UserId] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def write(thread_index: int) -> None:
        try:
            start.wait()
            for write_index in range(WRITES_PER_THREAD // 4):
                kind = thread_index % 3
                if kind == 0:
                    # A blind save of a fresh copy: always written.
                    copy = business_repo.get(business.id)
                    assert copy is not None
                    copy.name = BusinessName(f"Save {thread_index}.{write_index}")
                    business_repo.save(copy)
                    is_written = True
                elif kind == 1:
                    # A settings save: written only from the current revision.
                    copy = business_repo.get(business.id)
                    assert copy is not None
                    copy.name = BusinessName(f"Settings {thread_index}")
                    is_written = business_repo.save_if_unchanged(copy)
                else:
                    # A change of the business as stored (a member joins).
                    member_id = UserId()
                    business_repo.update(business.id, adding_member(member_id))
                    with lock:
                        added_members.append(member_id)
                    is_written = True

                if is_written:
                    with lock:
                        write_count.append(1)
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [
        threading.Thread(target=write, args=(thread_index,))
        for thread_index in range(THREAD_COUNT)
    ]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        stored = business_repo.get(business.id)
    finally:
        connection_pool.close()

    assert errors == []
    assert stored is not None
    # Every write raised the revision by exactly one: none shared a revision.
    assert int(stored.revision) == initial_revision + len(write_count)
    assert len(added_members) == (THREAD_COUNT // 3) * (WRITES_PER_THREAD // 4)


def test_concurrent_atomic_changes_are_never_lost(database_url: DatabaseUrl) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url,
        max_size=POOL_SIZE,
        acquire_timeout_seconds=30,
    )
    business_repo = BusinessRepository(
        PostgresCollectionFactory(
            connection_pool=connection_pool,
            storage_scope=StorageScopeContext(),
            wall_clock=build_ticking_wall_clock(),
        )(BusinessDocument, "businesses")
    )
    business = build_business(COUNTRY_SAMPLES[0], UserId())
    business_repo.save(business)
    start = threading.Barrier(THREAD_COUNT)
    added_members: list[UserId] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def add_members() -> None:
        try:
            start.wait()
            for _ in range(WRITES_PER_THREAD // 4):
                member_id = UserId()
                business_repo.update(business.id, adding_member(member_id))
                with lock:
                    added_members.append(member_id)
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [threading.Thread(target=add_members) for _ in range(THREAD_COUNT)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        stored = business_repo.get(business.id)
    finally:
        connection_pool.close()

    assert errors == []
    assert stored is not None
    assert {member.user_id for member in stored.members} == {
        business.members[0].user_id,
        *added_members,
    }
    assert int(stored.revision) == int(business.revision) + len(added_members)
