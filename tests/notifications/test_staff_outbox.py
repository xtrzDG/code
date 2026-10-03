"""Staff notifications in the outbox: limits, quiet hours, devices and states."""

import json

from typed_time_provider import Microseconds

from app.facilitators.notifications.push_notification_queue_facilitator import (
    PushNotificationQueueFacilitator,
)
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.notifications.staff_alerts import PushNotification, StaffAlertBrief
from app.schemas.exceptions.notification_errors import PushSubscriptionGoneError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    PushNotificationTag,
)
from app.schemas.typings.notifications.strings import StaffAlertTitle
from app.utilities.deliveries.delivery_keys import staff_recipient_key
from app.utilities.notifications.staff_delivery_keys import staff_delivery_state_id
from tests.channels.outbox_reads import outbox_of
from tests.channels.testbed import ChannelsTestbed
from tests.notifications.alert_world import AlertWorld

BUSINESS_ID: BusinessId = BusinessId()


def sms_contact() -> ManagerContact:
    return ManagerContact(
        name=ManagerName("Gio"),
        channel=ManagerContactChannel.SMS,
        address=ManagerContactAddress("+995555000222"),
        language=LanguageTag("ka"),
    )


def notify(
    testbed: ChannelsTestbed,
    contact: ManagerContact,
    deliver_after: Microseconds | None = None,
    handoff_id: HandoffId | None = None,
) -> bool:
    return testbed.staff_notifier.notify(
        StaffNotification(
            business_id=BUSINESS_ID,
            contact=contact,
            text=MessageText("New booking · Salobie Bia"),
            handoff_id=handoff_id,
            deliver_after=deliver_after,
        )
    )


def test_one_recipient_gets_at_most_its_hourly_share() -> None:
    testbed = ChannelsTestbed()

    queued = [notify(testbed, sms_contact()) for _ in range(11)]

    assert queued == [True] * 10 + [False]
    [refused] = [
        message
        for message in outbox_of(testbed, BUSINESS_ID)
        if message.status is OutboundMessageStatus.DEAD
    ]
    assert "Too many notifications" in str(refused.last_error)
    [state] = testbed.staff_delivery_state_repo.list_by_business(BUSINESS_ID)
    assert state.status is OutboundMessageStatus.DEAD
    assert state.id == staff_delivery_state_id(
        BUSINESS_ID, staff_recipient_key(sms_contact())
    )


def test_a_handoff_reaches_a_contact_once() -> None:
    testbed = ChannelsTestbed()
    handoff = HandoffId()

    assert notify(testbed, sms_contact(), handoff_id=handoff)
    assert notify(testbed, sms_contact(), handoff_id=handoff)

    assert len(outbox_of(testbed, BUSINESS_ID)) == 1


def test_held_notifications_wait_and_never_hold_back_an_urgent_one() -> None:
    testbed = ChannelsTestbed()
    morning = Microseconds(int(testbed.clock.now_microseconds()) + 3_600_000_000)

    notify(testbed, sms_contact(), deliver_after=morning)
    testbed.clock.advance(1)
    notify(testbed, sms_contact())
    testbed.run_worker()

    held, urgent = outbox_of(testbed, BUSINESS_ID)
    assert held.status is OutboundMessageStatus.PENDING
    assert held.next_attempt_at == morning
    assert urgent.status is OutboundMessageStatus.DELIVERED

    testbed.clock.advance(3_600)
    testbed.run_worker()

    assert outbox_of(testbed, BUSINESS_ID)[0].status is OutboundMessageStatus.DELIVERED
    [state] = testbed.staff_delivery_state_repo.list_by_business(BUSINESS_ID)
    assert state.status is OutboundMessageStatus.DELIVERED
    assert state.delivered_at == testbed.clock.now_microseconds()


def push_queue(testbed: ChannelsTestbed) -> PushNotificationQueueFacilitator:
    return PushNotificationQueueFacilitator(
        testbed.outbound_message_repo,
        testbed.job_queue,
        testbed.web_push_client,
        testbed.rate_limits,
        testbed.delivery_recorder,
        testbed.wall_clock,
    )


def device_notification(
    world: AlertWorld, testbed: ChannelsTestbed
) -> PushNotification:
    device = world.add_device(world.owner, "ka")
    testbed.push_subscription_repo.save(device)
    return PushNotification(
        business_id=world.business.id,
        subscription_id=device.id,
        user_id=world.owner,
        brief=StaffAlertBrief(title=StaffAlertTitle("ახალი ჯავშანი · Salobie Bia")),
        link=CabinetDeepLink("https://cabinet.example.com/n/" + "A" * 67),
        tag=PushNotificationTag("booking:booking_1"),
        is_urgent=True,
    )


def test_a_device_gets_the_encrypted_payload_the_service_worker_reads() -> None:
    testbed, world = ChannelsTestbed(), AlertWorld()
    notification = device_notification(world, testbed)

    assert push_queue(testbed).queue(notification)
    testbed.run_worker()

    [sent] = testbed.web_push_client.sent
    assert json.loads(str(sent.payload)) == {
        "title": "ახალი ჯავშანი · Salobie Bia",
        "body": "",
        "url": "https://cabinet.example.com/n/" + "A" * 67,
        "tag": "booking:booking_1",
    }
    assert sent.urgency.value == "high" and sent.topic == "booking:booking_1"
    [message] = outbox_of(testbed, world.business.id)
    assert message.status is OutboundMessageStatus.DELIVERED
    device = testbed.push_subscription_repo.get(
        world.business.id, notification.subscription_id
    )
    assert device is not None and device.delivered_at == message.delivered_at


def test_a_device_the_push_service_forgot_is_removed() -> None:
    testbed, world = ChannelsTestbed(), AlertWorld()
    notification = device_notification(world, testbed)
    testbed.web_push_client.error = PushSubscriptionGoneError("gone (HTTP 410)")

    push_queue(testbed).queue(notification)
    testbed.run_worker()

    [message] = outbox_of(testbed, world.business.id)
    assert message.status is OutboundMessageStatus.DEAD
    assert (
        testbed.push_subscription_repo.get(
            world.business.id, notification.subscription_id
        )
        is None
    )


def test_devices_are_skipped_while_push_is_off_and_limited_per_hour() -> None:
    testbed, world = ChannelsTestbed(), AlertWorld()
    notification = device_notification(world, testbed)
    off = PushNotificationQueueFacilitator(
        testbed.outbound_message_repo,
        testbed.job_queue,
        None,
        testbed.rate_limits,
        testbed.delivery_recorder,
        testbed.wall_clock,
    )

    assert not off.queue(notification)
    on = push_queue(testbed)
    assert [on.queue(notification) for _ in range(31)] == [True] * 30 + [False]
    handoff = notification.model_copy(update={"handoff_id": HandoffId()})
    second = PushNotificationQueueFacilitator(
        testbed.outbound_message_repo,
        testbed.job_queue,
        testbed.web_push_client,
        type(testbed.rate_limits)(),
        testbed.delivery_recorder,
        testbed.wall_clock,
    )
    assert second.queue(handoff) and second.queue(handoff)
    assert len(outbox_of(testbed, world.business.id)) == 32
