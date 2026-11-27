"""
Meta channels refused by the platform turn ERROR and heal; a health change
never undoes a token renewed or replaced meanwhile.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import ChannelRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.deliveries import DeliveryFailureReason
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.utilities.channels.channel_health import (
    mark_channel_failing,
    mark_channel_working,
    note_channel_refusal,
    summarize_channel_error,
)
from tests.channels.channels_fakes import FakeSecretCipher
from tests.channels.channels_settings import PAGE_ACCESS_TOKEN
from tests.channels.meta_payloads import PAGE_ID, page_message, page_webhook, post_meta
from tests.channels.stored_channels import stored
from tests.channels.testbed import ChannelsTestbed
from tests.live_events.recording_event_publisher import RecordingEventPublisher

NOW: Microseconds = Microseconds(1_790_812_800_000_000)
CIPHER = FakeSecretCipher()


class TestMetaChannelHealth:
    def test_expired_page_token_puts_messenger_in_error(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        channel = testbed.add_channel(
            business.id, ChannelKind.MESSENGER, PAGE_ID, PAGE_ACCESS_TOKEN
        )
        testbed.meta_transport.respond(
            "POST",
            r"/me/messages$",
            {
                "error": {
                    "message": "Error validating access token: Session has expired.",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
            status_code=400,
        )

        post_meta(
            testbed,
            page_webhook("page", PAGE_ID, [page_message("ps-1", "Hi", PAGE_ID)]),
        )
        testbed.run_worker()

        broken = stored(testbed, channel)
        assert broken.status is ChannelStatus.ERROR
        assert "(190)" in str(broken.last_error)
        assert "Session has expired" in str(broken.last_error)
        assert PAGE_ACCESS_TOKEN not in str(broken.last_error)

        testbed.meta_transport.respond("POST", r"/me/messages$", {"message_id": "m"})
        post_meta(
            testbed,
            page_webhook(
                "page", PAGE_ID, [page_message("ps-1", "Again", PAGE_ID, mid="m2")]
            ),
        )
        testbed.run_worker()
        assert stored(testbed, channel).status is ChannelStatus.CONNECTED

    def test_temporary_meta_failures_leave_the_channel_connected(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        channel = testbed.add_channel(
            business.id, ChannelKind.MESSENGER, PAGE_ID, PAGE_ACCESS_TOKEN
        )
        testbed.meta_transport.respond(
            "POST",
            r"/me/messages$",
            {"error": {"message": "Please retry", "code": 2}},
            status_code=500,
        )

        post_meta(
            testbed,
            page_webhook("page", PAGE_ID, [page_message("ps-1", "Hi", PAGE_ID)]),
        )
        testbed.run_worker()

        assert stored(testbed, channel).status is ChannelStatus.CONNECTED


def test_error_summaries_are_one_short_line() -> None:
    summary = summarize_channel_error("Line one\n  line two " + "x" * 400)

    assert "\n" not in str(summary)
    assert len(str(summary)) == 300
    assert str(summary).startswith("Line one line two x")
    assert str(summary).endswith("…")
    assert summarize_channel_error("   ") == (
        "The platform refused the channel's credential."
    )


def whatsapp_with(token: str, status: ChannelStatus) -> ChannelDocument:
    return ChannelDocument(
        business_id=BusinessId(),
        kind=ChannelKind.WHATSAPP,
        status=status,
        external_id=ChannelExternalId("106540352242923"),
        encrypted_secret=CIPHER.encrypt(ChannelSecret(token)),
    )


def test_a_token_renewed_meanwhile_is_never_undone() -> None:
    channels = ChannelRepository(InMemoryDocumentCollectionAdapter(ChannelDocument))
    events = RecordingEventPublisher()
    failing = whatsapp_with("EAAfake-token-1", ChannelStatus.ERROR)
    sent_with = failing.model_copy(update={"status": ChannelStatus.CONNECTED})
    renewed = sent_with.model_copy(
        update={"encrypted_secret": CIPHER.encrypt(ChannelSecret("EAAfake-token-2"))}
    )
    channels.save(renewed)

    mark_channel_failing(
        channels,
        events,
        sent_with,
        "Error validating access token (190)",
        NOW,
        DeliveryFailureReason.CREDENTIAL_REJECTED,
    )
    note_channel_refusal(channels, events, sent_with, "Recipient blocked", NOW)
    channels.save(renewed.model_copy(update={"status": ChannelStatus.ERROR}))
    mark_channel_working(channels, events, failing, NOW)

    stored_now = channels.get(renewed.id)
    assert stored_now is not None
    assert stored_now.encrypted_secret == renewed.encrypted_secret
    assert stored_now.status is ChannelStatus.ERROR
    assert stored_now.last_error is None
    assert events.events == []


def test_a_health_change_keeps_what_was_written_meanwhile() -> None:
    channels = ChannelRepository(InMemoryDocumentCollectionAdapter(ChannelDocument))
    events = RecordingEventPublisher()
    sent_with = whatsapp_with("EAAfake-token-1", ChannelStatus.CONNECTED)
    channels.save(sent_with.model_copy(update={"last_inbound_at": NOW}))

    mark_channel_failing(
        channels,
        events,
        sent_with,
        "Error validating access token (190)",
        NOW,
        DeliveryFailureReason.CREDENTIAL_REJECTED,
    )

    stored_now = channels.get(sent_with.id)
    assert stored_now is not None
    assert stored_now.status is ChannelStatus.ERROR
    assert stored_now.last_error_reason is DeliveryFailureReason.CREDENTIAL_REJECTED
    assert stored_now.last_inbound_at == NOW
    assert events.kinds() == [LiveEventKind.CHANNEL_ERROR]
