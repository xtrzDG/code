"""The channels testbed's worker flow for customer media: updates and reads."""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.channels.testbed import ChannelsTestbed
from tests.media.recorded_payloads import load_fixture

# Past the backoff of any attempt of a queued job.
PAST_EVERY_BACKOFF_SECONDS: int = 24 * 3600


def telegram_update(index: int) -> dict[str, Any]:
    update: dict[str, Any] = load_fixture("telegram_media_updates.json")[index]
    return update


def read_attachments(testbed: ChannelsTestbed) -> list[MessageAttachment]:
    [message] = testbed.pipeline.messages
    return list(message.attachments)


def transcription_usage(
    testbed: ChannelsTestbed, business_id: BusinessId
) -> list[UsageEventDocument]:
    return [
        event
        for event in testbed.usage_event_repo.list_by_business_between(
            business_id, Microseconds(0), Microseconds(2**62)
        )
        if event.kind is UsageKind.TRANSCRIPTION_SECONDS
    ]
