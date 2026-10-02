"""Reminder delivery: which channel and template reach the customer, and retries."""

import logging

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.use_cases.bookings.reminders.reminder_rules import (
    choose_reminder_identities,
)
from tests.operations.builders import DEFAULT_NOW
from tests.operations.fakes import to_microseconds
from tests.operations.reminder_scene import ReminderScene


def test_whatsapp_booking_is_reminded_in_georgian_in_the_business_time_zone() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.WHATSAPP: "995555123456"})
    scene.customer_wrote(contact, ChannelKind.WHATSAPP, hours_ago=3)
    booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")

    report = scene.run()

    assert report.processed_count == 1
    [(business_id, channel, user_id, text)] = scene.sender.sent
    assert business_id == scene.business.id
    assert channel is ChannelKind.WHATSAPP
    assert user_id == "995555123456"
    assert str(text).startswith("შეხსენება")
    assert "Salobie Bia" in str(text)
    assert "19:00" in str(text)  # 15:00 UTC is 19:00 in Tbilisi
    assert "Nino" in str(text)
    assert "უპასუხეთ ამ შეტყობინებას" in str(text)  # how to cancel or move it
    assert "Free cancellation up to 2 hours before." in str(text)
    assert scene.stored(booking).reminder_sent_at == to_microseconds(DEFAULT_NOW)
    assert scene.sender.templates == []
    assert scene.usage_events() == 0  # metered once, by the channel sender


def test_a_whatsapp_customer_silent_for_a_day_gets_the_approved_template() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.WHATSAPP: "995555123456"})
    scene.customer_wrote(contact, ChannelKind.WHATSAPP, hours_ago=72)
    booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")

    report = scene.run()

    assert report.processed_count == 1
    assert scene.sender.sent == []
    [(business_id, user_id, template, language, parameters)] = scene.sender.templates
    assert (business_id, user_id, template, language) == (
        scene.business.id,
        "995555123456",
        "booking_reminder",
        "ka",
    )
    business_name, date_text, time_text, name = parameters
    assert business_name == "Salobie Bia"
    assert "2026" in date_text
    assert time_text == "19:00"
    assert name == "Nino"
    assert scene.stored(booking).reminder_sent_at is not None
    assert scene.usage_events() == 0


def test_without_a_template_whatsapp_waits_for_another_messenger() -> None:
    scene = ReminderScene(reminder_template=None)
    only_whatsapp = scene.add_customer({ChannelKind.WHATSAPP: "995555123456"})
    silent = scene.add_booking(only_whatsapp, "2026-10-05T15:00:00+00:00")
    both = scene.add_customer(
        {ChannelKind.WHATSAPP: "995555000000", ChannelKind.TELEGRAM: "7001"}
    )
    scene.add_booking(both, "2026-10-05T16:00:00+00:00")

    report = scene.run()

    assert report.processed_count == 1
    assert [channel for _, channel, _, _ in scene.sender.sent] == [ChannelKind.TELEGRAM]
    assert scene.stored(silent).reminder_sent_at is None


def test_messenger_outside_its_window_is_not_written_to() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.MESSENGER: "psid-1"})
    scene.customer_wrote(contact, ChannelKind.MESSENGER, hours_ago=30)
    booking = scene.add_booking(
        contact, "2026-10-05T15:00:00+00:00", ChannelKind.MESSENGER
    )

    assert scene.run().processed_count == 0
    assert scene.sender.attempts == []
    assert scene.stored(booking).reminder_sent_at is None


def test_phone_booking_falls_back_to_a_messenger_the_customer_uses() -> None:
    scene = ReminderScene()
    contact = scene.add_customer(
        {ChannelKind.PHONE: "+995555123456", ChannelKind.TELEGRAM: "7001"}
    )
    scene.add_booking(contact, "2026-10-05T15:00:00+00:00", ChannelKind.PHONE)

    report = scene.run()

    assert report.processed_count == 1
    assert [(channel, user_id) for _, channel, user_id, _ in scene.sender.sent] == [
        (ChannelKind.TELEGRAM, "7001")
    ]
    assert scene.sender.templates == []  # Telegram is not a WhatsApp template


@pytest.mark.parametrize("source", [ChannelKind.PHONE, ChannelKind.WEB_CHAT])
def test_customers_known_only_by_phone_or_web_chat_are_skipped(
    source: ChannelKind,
) -> None:
    scene = ReminderScene()
    contact = scene.add_customer(
        {ChannelKind.PHONE: "+995555123456", ChannelKind.WEB_CHAT: "widget-1"}
    )
    booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00", source)

    report = scene.run()

    assert report.processed_count == 0
    assert scene.sender.attempts == []
    assert scene.stored(booking).reminder_sent_at is None


def test_failed_channel_falls_back_to_the_next_messenger() -> None:
    scene = ReminderScene(failing_channels=frozenset({ChannelKind.WHATSAPP}))
    contact = scene.add_customer(
        {ChannelKind.WHATSAPP: "995555123456", ChannelKind.INSTAGRAM: "ig-1"}
    )
    scene.customer_wrote(contact, ChannelKind.INSTAGRAM, hours_ago=1)
    scene.add_booking(contact, "2026-10-05T15:00:00+00:00", ChannelKind.WHATSAPP)

    report = scene.run()

    assert report.processed_count == 1
    assert scene.sender.attempts == [ChannelKind.WHATSAPP, ChannelKind.INSTAGRAM]
    assert scene.sender.templates == []


def test_delivery_failure_is_logged_and_retried_on_the_next_run(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scene = ReminderScene(failing_channels=frozenset({ChannelKind.WHATSAPP}))
    contact = scene.add_customer({ChannelKind.WHATSAPP: "995555123456"})
    booking = scene.add_booking(contact, "2026-10-05T15:00:00+00:00")

    with caplog.at_level(logging.WARNING):
        failed = scene.run()

    assert failed.processed_count == 0
    assert scene.stored(booking).reminder_sent_at is None
    assert scene.sender.templates == []
    assert "whatsapp" in caplog.text

    scene.sender.failing_channels.clear()
    retried = scene.run()

    assert retried.processed_count == 1
    assert scene.stored(booking).reminder_sent_at is not None
    assert len(scene.sender.templates) == 1


def test_reminder_identities_prefer_the_booking_channel_then_messengers() -> None:
    contact = ContactDocument(
        business_id=BusinessId(),
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.PHONE, channel_user_id=ChannelUserId("p")
            ),
            ChannelIdentity(
                channel=ChannelKind.INSTAGRAM, channel_user_id=ChannelUserId("i")
            ),
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP, channel_user_id=ChannelUserId("w")
            ),
            ChannelIdentity(
                channel=ChannelKind.TELEGRAM, channel_user_id=ChannelUserId("t")
            ),
        ],
    )

    from_instagram = choose_reminder_identities(contact, ChannelKind.INSTAGRAM)
    from_phone = choose_reminder_identities(contact, ChannelKind.PHONE)

    assert [identity.channel_user_id for identity in from_instagram] == [
        "i",
        "t",
        "w",
    ]
    assert [identity.channel_user_id for identity in from_phone] == ["t", "w", "i"]
