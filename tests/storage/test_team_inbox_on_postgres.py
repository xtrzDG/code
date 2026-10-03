"""
The team inbox on Postgres: of many simultaneous assignments one wins, a
turn's save never undoes an assignment, and the views and their counts
(the "nobody assigned" view reads a null lookup column) match.
"""

import threading

from typed_time_provider import Microseconds

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.conversation_repositories import ConversationRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.inbox import InboxView
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.assignment import ConversationAssignmentChange
from app.schemas.dto.inbox.inbox_views import InboxViewCounts, InboxViewFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from app.schemas.typings.platform.constrained_integers import (
    KeysetReadLimit,
    ListItemCount,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.concurrency_limits import POOL_SIZE, THREAD_COUNT
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.storage_testing import build_ticking_wall_clock

BUSINESS: BusinessId = BusinessId()
NOW: int = 1_791_018_000_000_000
EVERYTHING = KeysetSlice(limit=KeysetReadLimit(50))


def build_repository(
    connection_pool: PostgresConnectionPoolClient, storage_scope: StorageScopeContext
) -> ConversationRepository:
    return ConversationRepository(
        PostgresCollectionFactory(
            connection_pool=connection_pool,
            storage_scope=storage_scope,
            wall_clock=build_ticking_wall_clock(),
        )(ConversationDocument, "conversations")
    )


def conversation(
    minutes_ago: int,
    status: ConversationStatus = ConversationStatus.OPEN,
    has_open_request: bool = False,
    is_sandbox: bool = False,
) -> ConversationDocument:
    at = Microseconds(NOW - minutes_ago * 60_000_000)
    return ConversationDocument(
        business_id=BUSINESS,
        contact_id=ContactId(),
        assistant_version_id=AssistantVersionId(),
        channel=ChannelKind.TELEGRAM,
        channel_user_id=ChannelUserId(f"customer-{minutes_ago}"),
        status=status,
        has_open_request=has_open_request,
        is_sandbox=is_sandbox,
        last_message_at=at,
        created_at=at,
        updated_at=at,
    )


def assignment(to: UserId | None, revision: int) -> ConversationAssignmentChange:
    return ConversationAssignmentChange(
        assignee_user_id=to,
        assigned_by=to,
        expected_revision=AssignmentRevision(revision),
        at=Microseconds(NOW),
    )


def test_of_simultaneous_assignments_exactly_one_wins(
    database_url: DatabaseUrl,
) -> None:
    connection_pool = PostgresConnectionPoolClient(
        database_url, max_size=POOL_SIZE, acquire_timeout_seconds=30
    )
    storage_scope = StorageScopeContext()
    repository = build_repository(connection_pool, storage_scope)
    waiting = conversation(1, ConversationStatus.HANDOFF)
    with storage_scope.scoped_to_business(BUSINESS):
        repository.save(waiting)
    members = [UserId() for _ in range(THREAD_COUNT)]
    winners: list[UserId] = []
    errors: list[BaseException] = []
    start = threading.Barrier(THREAD_COUNT)
    lock = threading.Lock()

    def take(member: UserId) -> None:
        try:
            start.wait()
            with storage_scope.scoped_to_business(BUSINESS):
                taken = repository.assign(BUSINESS, waiting.id, assignment(member, 0))
            if taken is not None:
                with lock:
                    winners.append(member)
        except BaseException as error:  # pragma: no cover - reported below
            errors.append(error)

    threads = [threading.Thread(target=take, args=(member,)) for member in members]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        with storage_scope.scoped_to_business(BUSINESS):
            stored = repository.get(BUSINESS, waiting.id)
    finally:
        connection_pool.close()

    assert errors == []
    assert len(winners) == 1
    assert stored is not None
    assert stored.assignee_user_id == winners[0]
    assert stored.assignment_revision == 1


def test_a_stale_save_of_a_turn_keeps_the_assignment(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    repository = ConversationRepository(
        postgres_collections(ConversationDocument, "conversations")
    )
    member = UserId()
    with storage_scope.scoped_to_business(BUSINESS):
        waiting = conversation(5, has_open_request=True)
        repository.save(waiting)
        loaded_by_the_turn = repository.get(BUSINESS, waiting.id)
        assert loaded_by_the_turn is not None
        assert repository.assign(BUSINESS, waiting.id, assignment(member, 0))

        # The turn, which loaded the conversation before the assignment,
        # saves it a minute later with a person needed.
        loaded_by_the_turn.status = ConversationStatus.HANDOFF
        loaded_by_the_turn.last_message_at = Microseconds(NOW)
        repository.save(loaded_by_the_turn)
        stored = repository.get(BUSINESS, waiting.id)

    assert stored is not None
    assert stored.status is ConversationStatus.HANDOFF
    assert stored.last_message_at == NOW
    assert (stored.assignee_user_id, stored.assignment_revision) == (member, 1)
    assert stored.has_open_request is True
    assert stored.awaits_team is True


def test_views_and_counts_match_on_postgres(
    postgres_collections: PostgresCollectionFactory,
    storage_scope: StorageScopeContext,
) -> None:
    repository = ConversationRepository(
        postgres_collections(ConversationDocument, "conversations")
    )
    viewer, colleague = UserId(), UserId()
    mine = conversation(1, ConversationStatus.HANDOFF)
    theirs = conversation(2, has_open_request=True)
    nobody_handoff = conversation(3, ConversationStatus.HANDOFF)
    nobody_request = conversation(4, has_open_request=True)
    quiet = conversation(5)
    sandbox = conversation(6, ConversationStatus.HANDOFF, is_sandbox=True)
    with storage_scope.scoped_to_business(BUSINESS):
        for stored in (mine, theirs, nobody_handoff, nobody_request, quiet, sandbox):
            repository.save(stored)
        repository.assign(BUSINESS, mine.id, assignment(viewer, 0))
        repository.assign(BUSINESS, theirs.id, assignment(colleague, 0))
        pages: dict[InboxView, list[ConversationId]] = {
            name: [
                item.id
                for item in repository.page_inbox(
                    BUSINESS, EVERYTHING, InboxViewFilter(view=name, viewer=viewer)
                )
            ]
            for name in InboxView
        }
        counts = repository.count_inbox(BUSINESS, viewer)
        workload = repository.count_awaiting_by_assignee(BUSINESS)

    assert pages == {
        InboxView.NEEDS_PERSON: [mine.id, nobody_handoff.id],
        InboxView.REQUESTS: [theirs.id, nobody_request.id],
        InboxView.MINE: [mine.id],
        InboxView.UNASSIGNED: [nobody_handoff.id, nobody_request.id],
        InboxView.ALL: [
            mine.id,
            theirs.id,
            nobody_handoff.id,
            nobody_request.id,
            quiet.id,
        ],
    }
    assert counts == InboxViewCounts(
        needs_person=ListItemCount(2),
        requests=ListItemCount(2),
        mine=ListItemCount(1),
        unassigned=ListItemCount(2),
    )
    assert workload == {viewer: 1, colleague: 1}
