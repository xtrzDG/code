"""
The nightly retention purge on the in-memory and the Postgres storage:
what goes past each period, what stays, the audit counts, the processor
deletions it queues, and a second run that finds nothing more.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.processor_erasure import ProcessorErasureJobPayload
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.privacy.constrained_integers import (
    ConversationRetentionDays,
    LlmTurnRetentionDays,
)
from app.utilities.privacy.retention_keys import privacy_settings_id_of
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.conftest import CollectionFactory
from tests.storage.retention_world import START_MICROSECONDS, RetentionWorld

pytestmark = pytest.mark.usefixtures("platform_scope")


def tick() -> JobTick:
    return JobTick(
        job_name=JobName("purge_expired_personal_data"),
        scheduled_at=Microseconds(START_MICROSECONDS),
    )


def test_defaults_keep_conversations_two_years_and_model_records_a_month(
    collections: CollectionFactory,
) -> None:
    world = RetentionWorld(collections)
    business = world.new_business()
    expired = world.history(business, days_ago=800)
    quiet = world.history(business, days_ago=45)
    fresh = world.history(business, days_ago=2)

    report = world.purge.run(tick())

    # Past two years: the content goes, the business records stay anonymous.
    assert (
        world.messages.list_by_conversation(business.id, expired.conversation.id) == []
    )
    assert world.notes.list_by_conversation(business.id, expired.conversation.id) == []
    call = world.calls.get(business.id, expired.call.id)
    assert call is not None
    assert (call.transcript, call.recording_path, call.summaries) == (None, None, [])
    assert (call.from_phone_number, call.to_phone_number) == (None, None)
    assert world.recordings.deleted_paths == [expired.call.recording_path]
    assert world.media.get(business.id, expired.media.id) is None
    assert set(world.media_storage.files) == {
        (str(business.id), str(history.media.storage_path))
        for history in (quiet, fresh)
    }
    lead = world.leads.get(business.id, expired.lead.id)
    assert lead is not None and str(lead.details).startswith("[removed")
    assert lead.budget is None
    booking = world.bookings.get(business.id, expired.booking.id)
    assert booking is not None and booking.notes is None
    handoff = world.handoffs.get(business.id, expired.handoff.id)
    assert handoff is not None and str(handoff.summary).startswith("[removed")
    assert world.missed_calls.get(business.id, expired.missed_call.id) is None
    assert world.conversations.get(business.id, expired.conversation.id) is not None

    # Quiet for 45 days: only the model's records go; the conversation stays.
    assert world.turns.list_by_conversation(expired.conversation.id) == []
    assert world.turns.list_by_conversation(quiet.conversation.id) == []
    assert (
        len(world.messages.list_by_conversation(business.id, quiet.conversation.id))
        == 2
    )
    quiet_lead = world.leads.get(business.id, quiet.lead.id)
    assert quiet_lead is not None and quiet_lead.budget is not None

    # Two days old: nothing is touched.
    assert len(world.turns.list_by_conversation(fresh.conversation.id)) == 3
    assert (
        len(world.notes.list_by_conversation(business.id, fresh.conversation.id)) == 1
    )

    assert world.retention_entries(business) == {
        "messages": 2,
        "llm_turns": 6,
        "conversation_note": 1,
        "message_media": 1,
        "missed_call": 1,
        "call": 1,
        "lead": 1,
        "booking": 1,
        "handoff": 1,
    }
    assert int(report.processed_count) == 15
    state = world.states.get_or_new(business.id)
    assert state.last_run_at is not None
    assert int(state.last_counts.deleted_llm_turns) == 6


def test_the_processor_copies_of_what_went_are_queued_for_deletion(
    collections: CollectionFactory,
) -> None:
    world = RetentionWorld(collections)
    business = world.new_business()
    expired = world.history(business, days_ago=800)
    quiet = world.history(business, days_ago=45)

    world.purge.run(tick())

    payloads = [
        ProcessorErasureJobPayload.model_validate_json(str(job.payload))
        for job in world.processors.job_queue.jobs
    ]
    assert {payload.processor.value for payload in payloads} == {
        "langfuse",
        "elevenlabs",
    }
    langfuse = next(p for p in payloads if p.processor.value == "langfuse")
    elevenlabs = next(p for p in payloads if p.processor.value == "elevenlabs")
    assert set(langfuse.conversation_ids) == {
        expired.conversation.id,
        quiet.conversation.id,
    }
    assert elevenlabs.provider_call_ids == [expired.call.provider_call_id]
    assert {job.business_id for job in world.processors.job_queue.jobs} == {business.id}
    assert {payload.reason.value for payload in payloads} == {"retention"}


def test_a_second_run_finds_nothing_more_and_writes_nothing(
    collections: CollectionFactory,
) -> None:
    world = RetentionWorld(collections)
    business = world.new_business()
    world.history(business, days_ago=800)
    world.purge.run(tick())
    entries_after_first = len(world.audit.list_by_business(business.id))
    queued_after_first = len(world.processors.job_queue.jobs)

    world.clock.now += 3_600_000_000
    report = world.purge.run(tick())

    assert int(report.processed_count) == 0
    assert len(world.audit.list_by_business(business.id)) == entries_after_first
    assert len(world.processors.job_queue.jobs) == queued_after_first
    state = world.states.get_or_new(business.id)
    assert int(state.last_counts.deleted_messages) == 0


def test_the_business_periods_decide_and_a_longer_one_never_brings_data_back(
    collections: CollectionFactory,
    platform_scope: StorageScopeContext,
) -> None:
    del platform_scope
    world = RetentionWorld(collections)
    strict = world.new_business()
    lenient = world.new_business()
    world.settings.save(
        BusinessPrivacySettingsDocument(
            id=privacy_settings_id_of(strict.id),
            business_id=strict.id,
            conversation_retention_days=ConversationRetentionDays(30),
            llm_turn_retention_days=LlmTurnRetentionDays(7),
        )
    )
    strict_history = world.history(strict, days_ago=40)
    strict_recent = world.history(strict, days_ago=10)
    lenient_history = world.history(lenient, days_ago=40)

    world.purge.run(tick())

    assert (
        world.messages.list_by_conversation(strict.id, strict_history.conversation.id)
        == []
    )
    assert world.turns.list_by_conversation(strict_recent.conversation.id) == []
    assert (
        len(
            world.messages.list_by_conversation(
                strict.id, strict_recent.conversation.id
            )
        )
        == 2
    )
    assert (
        len(
            world.messages.list_by_conversation(
                lenient.id, lenient_history.conversation.id
            )
        )
        == 2
    )
    cutoff = world.states.get_or_new(strict.id).conversations_purged_before

    world.settings.save(
        BusinessPrivacySettingsDocument(
            id=privacy_settings_id_of(strict.id),
            business_id=strict.id,
            conversation_retention_days=ConversationRetentionDays(365),
        )
    )
    world.clock.now += 86_400_000_000
    world.purge.run(tick())

    assert world.states.get_or_new(strict.id).conversations_purged_before == cutoff
