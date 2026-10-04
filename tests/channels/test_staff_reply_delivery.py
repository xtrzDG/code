"""
A staff reply goes through the outbox like every message to a customer: a
provider outage is retried and the customer gets it once, the card follows
its delivery (sending, retrying, delivered, failed with the reason), and a
WhatsApp template Meta refuses is given up without an English retry.
"""

import json

from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.conversations import StaffMessageDelivery
from app.schemas.constants.deliveries import (
    DeliveryFailureReason,
    OutboundDeliveryState,
    OutboundMessageKind,
    OutboundMessageStatus,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.conversation_actions import (
    SendStaffMessageCommand,
)
from app.schemas.dto.conversation_feed.message_deliveries import MessageDeliveryView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.constrained_strings import StaffReplyText
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.transformers.conversations.message_view_transformer import (
    MessageViewTransformer,
)
from app.use_cases.conversations.send_staff_message_use_case import (
    SendStaffMessageUseCase,
)
from app.use_cases.conversations.staff_reply_deliveries import (
    staff_reply_outbox_id,
)
from app.utilities.deliveries.delivery_views import build_delivery_view
from tests.channels.channels_payloads import telegram_ok
from tests.channels.customer_outbox import queue_customer_message, template
from tests.channels.outbox_reads import outbox_of
from tests.channels.stored_channels import stored
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed

STAFF_TEXT: str = "We kept the table by the window for you."
META_REFUSAL: dict[str, object] = {
    "error": {"message": "(#132001) Template name does not exist", "code": 132001}
}
META_REVOKED: dict[str, object] = {
    "error": {
        "message": "Error validating access token: Session has expired.",
        "type": "OAuthException",
        "code": 190,
    }
}


class AnyMemberMayWrite(UseCaseContract[BusinessAccessRequest, BusinessDocument]):
    def __init__(self, testbed: ChannelsTestbed) -> None:
        self._testbed: ChannelsTestbed = testbed

    def run(self, input_data: BusinessAccessRequest) -> BusinessDocument:
        business = self._testbed.business_repo.get(input_data.business_id)
        if business is None:
            raise NotFoundError("No such business.")

        return business


def staff_replies(testbed: ChannelsTestbed) -> SendStaffMessageUseCase:
    return SendStaffMessageUseCase(
        AnyMemberMayWrite(testbed),
        testbed.conversation_repo,
        testbed.message_repo,
        testbed.channel_repo,
        testbed.audit_log_repo,
        testbed.outbound_message_repo,
        testbed.job_queue,
        MessageViewTransformer(),
        testbed.live_events,
        testbed.wall_clock,
    )


def delivery_of(
    testbed: ChannelsTestbed, business: BusinessDocument, message_id: MessageId
) -> MessageDeliveryView:
    """What the conversation card shows next to the staff reply now."""

    outbound = testbed.outbound_message_repo.get(
        business.id, staff_reply_outbox_id(business.id, message_id)
    )
    assert outbound is not None
    return build_delivery_view(outbound)


def test_a_provider_500_on_a_staff_reply_is_retried_and_delivered_once() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    post_update(testbed, channel, build_update())
    testbed.run_worker()
    testbed.telegram_transport.respond_in_turn(
        "POST",
        r"/sendMessage$",
        [
            (500, {"ok": False, "error_code": 500, "description": "Internal"}),
            (200, telegram_ok({"message_id": 100})),
        ],
    )

    result = staff_replies(testbed).run(
        SendStaffMessageCommand(
            user_id=testbed.add_user("staff"),
            business_id=business.id,
            conversation_id=testbed.pipeline.conversation_id,
            text=StaffReplyText(STAFF_TEXT),
        )
    )

    assert result.delivery is StaffMessageDelivery.SENT
    assert result.message.delivery is not None
    assert result.message.delivery.state is OutboundDeliveryState.SENDING

    testbed.run_worker()
    retrying = delivery_of(testbed, business, result.message.id)
    assert retrying.state is OutboundDeliveryState.RETRYING
    assert retrying.failure_reason is DeliveryFailureReason.PROVIDER_UNAVAILABLE
    assert retrying.attempts == 1
    assert retrying.next_attempt_at is not None

    testbed.clock.advance(10)
    testbed.run_worker()
    testbed.clock.advance(3600)
    testbed.run_worker()

    delivered = delivery_of(testbed, business, result.message.id)
    assert delivered.state is OutboundDeliveryState.DELIVERED
    assert delivered.failure_reason is None
    assert delivered.attempts == 2
    staff_sends = [
        request
        for request in testbed.telegram_transport.requests_to("/sendMessage")
        if request.json()["text"] == STAFF_TEXT
    ]
    assert len(staff_sends) == 2  # the refused attempt and the delivered one
    [outbound] = [
        message
        for message in outbox_of(testbed, business.id)
        if message.kind is OutboundMessageKind.STAFF_REPLY
    ]
    assert outbound.status is OutboundMessageStatus.DELIVERED
    assert outbound.provider_message_id == "555000111:100"


def whatsapp_message(
    testbed: ChannelsTestbed, kind: OutboundMessageKind, name: str
) -> tuple[BusinessDocument, OutboundMessageDocument]:
    owner = testbed.add_user("owner")
    business = testbed.add_business(owner)
    channel = testbed.add_channel(business.id, ChannelKind.WHATSAPP, "106540352242922")
    queued = queue_customer_message(
        testbed,
        channel,
        "995599123456",
        kind,
        message_template=template(name, "ka", ["Salobie Bia"]),
    )
    return business, queued


def test_a_refused_staff_template_fails_without_an_english_retry() -> None:
    testbed = ChannelsTestbed()
    testbed.meta_transport.respond("POST", r"/messages$", META_REFUSAL, status_code=404)
    business, queued = whatsapp_message(
        testbed, OutboundMessageKind.STAFF_REPLY, "staff_reply"
    )

    testbed.run_worker()

    [request] = testbed.meta_transport.requests
    assert json.loads(request.body)["template"]["language"]["code"] == "ka"
    failed = testbed.outbound_message_repo.get(business.id, queued.id)
    assert failed is not None
    assert failed.status is OutboundMessageStatus.DEAD
    assert failed.last_failure_reason is DeliveryFailureReason.TEMPLATE_REJECTED
    view = build_delivery_view(failed)
    assert view.state is OutboundDeliveryState.FAILED
    assert view.failure_reason is DeliveryFailureReason.TEMPLATE_REJECTED


def test_a_revoked_token_on_a_template_marks_whatsapp_and_skips_english() -> None:
    testbed = ChannelsTestbed()
    testbed.meta_transport.respond("POST", r"/messages$", META_REVOKED, status_code=401)
    business, queued = whatsapp_message(
        testbed, OutboundMessageKind.BOOKING_REMINDER, "booking_reminder"
    )
    [channel] = testbed.channel_repo.list_by_business(business.id)

    testbed.run_worker()

    [request] = testbed.meta_transport.requests  # no English retry
    assert json.loads(request.body)["template"]["language"]["code"] == "ka"
    broken = stored(testbed, channel)
    assert broken.status is ChannelStatus.ERROR
    assert "(190)" in str(broken.last_error)
    failed = testbed.outbound_message_repo.get(business.id, queued.id)
    assert failed is not None
    assert failed.status is OutboundMessageStatus.DEAD
    assert failed.last_failure_reason is DeliveryFailureReason.CREDENTIAL_REJECTED
    assert UsageKind.WHATSAPP_TEMPLATE not in [
        event.kind
        for event in testbed.usage_event_repo.list_by_business_between(
            business.id,
            Microseconds(0),
            Microseconds(int(testbed.clock.now_microseconds()) + 1),
        )
    ]
