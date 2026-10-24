"""Customer messages, channel health and autotest progress reach open cabinets."""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import ChannelRepository
from app.schemas.constants.assistants import AutotestRunStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.channels.channel_health import (
    mark_channel_failing,
    mark_channel_working,
    note_channel_refusal,
)
from tests.assembly.autotest_run_helpers import start
from tests.assembly.testbed import AssemblyTestbed
from tests.brain.brain_world import build_world
from tests.brain.scripted_turns import say, scripted
from tests.live_events.recording_event_publisher import (
    PublishedLiveEvent,
    RecordingEventPublisher,
)

NOW: Microseconds = Microseconds(1_790_812_800_000_000)


def test_the_customer_message_and_the_answer_are_both_announced() -> None:
    world = build_world(scripted(say("Hello!"), say("Hello again!")))

    world.send("Hi")
    conversation = world.conversations()[0]
    world.send("Test", is_sandbox=True)

    # A new conversation is also announced as started (for webhooks; the
    # cabinet's live stream does not carry it).
    started = PublishedLiveEvent(
        world.business.id, LiveEventKind.CONVERSATION_STARTED, (str(conversation.id),)
    )
    message = PublishedLiveEvent(
        world.business.id, LiveEventKind.CONVERSATION_MESSAGE, (str(conversation.id),)
    )
    assert world.live_events.events == [started, message, message]


def test_channel_health_changes_are_announced_and_unchanged_health_is_not() -> None:
    channels = ChannelRepository(InMemoryDocumentCollectionAdapter(ChannelDocument))
    events = RecordingEventPublisher()
    channel = ChannelDocument(
        business_id=BusinessId(),
        kind=ChannelKind.TELEGRAM,
        status=ChannelStatus.CONNECTED,
    )
    channels.save(channel)

    mark_channel_working(channels, events, channel, NOW)
    note_channel_refusal(channels, events, channel, "Bot was blocked by the user", NOW)
    mark_channel_working(channels, events, channel, NOW)
    mark_channel_failing(channels, events, channel, "401 Unauthorized", NOW)
    mark_channel_working(channels, events, channel, NOW)
    channel.status = ChannelStatus.DISABLED
    mark_channel_failing(channels, events, channel, "401 Unauthorized", NOW)

    assert events.kinds() == [
        LiveEventKind.CHANNEL_CHANGED,
        LiveEventKind.CHANNEL_CHANGED,
        LiveEventKind.CHANNEL_ERROR,
        LiveEventKind.CHANNEL_CHANGED,
    ]
    assert {published.ids for published in events.events} == {(str(channel.id),)}


def test_an_autotest_run_reports_its_start_progress_and_end() -> None:
    testbed = AssemblyTestbed()
    business, version = start(testbed)

    started = testbed.queue_autotest_run_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id, business_id=business.id, version_id=version.id
        )
    )
    testbed.run_worker()

    stored = testbed.run_repo.get(business.id, started.id)
    assert stored is not None and stored.status is AutotestRunStatus.FINISHED
    events = testbed.autotest_events.events
    assert {published.event for published in events} == {
        LiveEventKind.AUTOTEST_PROGRESS
    }
    assert len(events) >= 3
    assert {published.ids for published in events} == {
        (str(started.id), str(version.id))
    }
