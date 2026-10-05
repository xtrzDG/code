"""
Rules of the retention purge beyond the periods: a failing business does
not stop the others, the voice platform's recordings go through the
queued deletion, an upcoming visit keeps its notes, the cutoffs never move
back, and on Postgres the deletes run in transactions of at most 1,000
rows.
"""

from collections.abc import Generator
from contextlib import contextmanager

import pytest
from typed_time_provider import Microseconds

from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.repositories.retention_record_repositories import ExpiredMessageRepository
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.processor_erasure import ProcessorErasureJobPayload
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.bookings.constrained_integers import BookingEndsAtUnixSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import DatabaseUrl
from app.use_cases.compliance.retention.purge_expired_personal_data_use_case import (
    latest,
)
from app.use_cases.compliance.retention.retention_audit import window_since
from app.utilities.channels.voice_recordings import build_voice_platform_recording_path
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import InMemoryCollectionFactory, PostgresCollectionFactory
from tests.storage.retention_world import START_MICROSECONDS, RetentionWorld
from tests.storage.storage_testing import build_fixed_wall_clock

TICK: JobTick = JobTick(
    job_name=JobName("purge_expired_personal_data"),
    scheduled_at=Microseconds(START_MICROSECONDS),
)


def in_memory_world() -> RetentionWorld:
    return RetentionWorld(InMemoryCollectionFactory())


def test_a_failing_business_does_not_stop_the_others_and_is_tried_again() -> None:
    world = in_memory_world()
    failing = world.new_business()
    healthy = world.new_business()
    world.history(failing, days_ago=800)
    quiet = world.history(healthy, days_ago=45)
    world.recordings.is_failing = True

    with pytest.raises(ExternalServiceError):
        world.purge.run(TICK)

    assert world.turns.list_by_conversation(quiet.conversation.id) == []
    assert world.states.get_or_new(healthy.id).last_run_at is not None
    assert world.states.get_or_new(failing.id).last_run_at is None

    world.recordings.is_failing = False
    world.purge.run(TICK)

    assert world.retention_entries(failing)["call"] == 1


def test_a_recording_the_voice_platform_keeps_goes_with_its_queued_deletion() -> None:
    world = in_memory_world()
    business = world.new_business()
    history = world.history(business, days_ago=800)
    on_the_platform = history.call.model_copy(
        update={
            "recording_path": build_voice_platform_recording_path(
                history.call.provider_call_id
            )
        }
    )
    world.calls.save(on_the_platform)

    world.purge.run(TICK)

    assert world.recordings.deleted_paths == []
    call = world.calls.get(business.id, history.call.id)
    assert call is not None and call.recording_path is None
    queued = [
        ProcessorErasureJobPayload.model_validate_json(str(job.payload))
        for job in world.processors.job_queue.jobs
    ]
    assert [history.call.provider_call_id] in [
        payload.provider_call_ids for payload in queued
    ]


def test_an_upcoming_visit_keeps_its_notes_however_old_the_booking() -> None:
    world = in_memory_world()
    business = world.new_business()
    history = world.history(business, days_ago=800)
    upcoming = history.booking.model_copy(
        update={
            "ends_at": BookingEndsAtUnixSeconds(
                (START_MICROSECONDS // 1_000_000) + 86_400
            )
        }
    )
    world.bookings.save(upcoming)

    world.purge.run(TICK)

    booking = world.bookings.get(business.id, history.booking.id)
    assert booking is not None and booking.notes is not None


def test_a_window_starts_where_the_last_purge_ended_and_cutoffs_never_move_back() -> (
    None
):
    earlier, later = Microseconds(100), Microseconds(200)

    assert window_since(None, later) is not None
    window = window_since(earlier, later)
    assert window is not None and (window.since, window.before) == (earlier, later)
    assert window_since(later, earlier) is None
    assert window_since(later, later) is None
    assert latest(None, earlier) == earlier
    assert latest(later, earlier) == later
    assert latest(earlier, later) == later


class CountingConnectionPool(PostgresConnectionPoolClient):
    """The pool, counting the transactions it opens."""

    transactions: int = 0

    @contextmanager
    def transaction(self) -> Generator[PostgresConnection]:
        self.transactions += 1
        with super().transaction() as connection:
            yield connection


def test_old_messages_are_deleted_in_transactions_of_a_thousand_rows_on_postgres(
    database_url: DatabaseUrl,
    platform_scope: StorageScopeContext,
) -> None:
    pool = CountingConnectionPool(database_url, max_size=2)
    try:
        collection = PostgresCollectionFactory(
            pool, platform_scope, build_fixed_wall_clock()
        )(MessageDocument, "messages")
        business_id, conversation_id = BusinessId(), ConversationId()
        old = Microseconds(START_MICROSECONDS - 1_000)
        collection.upsert_many(
            [
                (str(message.id), message)
                for message in (
                    MessageDocument(
                        conversation_id=conversation_id,
                        business_id=business_id,
                        direction=MessageDirection.INBOUND,
                        author=MessageAuthor.CUSTOMER,
                        text=MessageText(f"message {index}"),
                        language=LanguageTag("en"),
                        created_at=old,
                        updated_at=old,
                    )
                    for index in range(2_500)
                )
            ]
        )
        pool.transactions = 0

        deleted = ExpiredMessageRepository(collection).delete_created_before(
            business_id, Microseconds(START_MICROSECONDS)
        )

        assert deleted == 2_500
        # 1,000 + 1,000 + 500 rows: three transactions, none holding more.
        assert pool.transactions == 3
    finally:
        pool.close()
