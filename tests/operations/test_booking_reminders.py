"""Booking reminders: the periodic job and the reminder text."""

import logging
from collections.abc import Callable
from datetime import datetime

import pytest
from typed_time_provider import Microseconds

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.schemas.constants.bookings import BookingStatus, BookingUnit, ResourceKind
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingView, RescheduleBookingCommand
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.operations import BookingMessageInput
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.bookings.constrained_integers import (
    BookingReminderLeadSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.profiles.strings import CancellationPolicyText
from app.transformers.notifications.booking_reminder_template_transformer import (
    BookingReminderTemplateTransformer,
)
from app.transformers.notifications.booking_reminder_transformer import (
    BookingReminderTransformer,
)
from app.use_cases.bookings.send_booking_reminders_use_case import (
    SendBookingRemindersUseCase,
    choose_reminder_identities,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.operations.builders import DEFAULT_NOW, OperationsWorld
from tests.operations.fakes import to_microseconds

# DEFAULT_NOW is Monday 2026-10-05 08:00 UTC = 12:00 in Tbilisi (UTC+4).
TICK: JobTick = JobTick(
    job_name=JobName("send_booking_reminders"),
    scheduled_at=to_microseconds(DEFAULT_NOW),
)


class RecordingChannelSender(ChannelMessageSenderFacilitatorContract):
    """Records proactive messages; channels listed as failing raise."""

    def __init__(self, failing_channels: frozenset[ChannelKind] = frozenset()) -> None:
        self.failing_channels: set[ChannelKind] = set(failing_channels)
        self.attempts: list[ChannelKind] = []
        self.sent: list[tuple[BusinessId, ChannelKind, ChannelUserId, MessageText]] = []
        self.templates: list[tuple[BusinessId, ChannelUserId, str, str, list[str]]] = []
        self.on_send: Callable[[], None] | None = None

    def send(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
        text: MessageText,
    ) -> None:
        self.attempts.append(channel)
        if self.on_send is not None:
            self.on_send()

        if channel in self.failing_channels:
            raise ExternalServiceError(f"The {channel.value} channel is not connected.")

        self.sent.append((business_id, channel, channel_user_id, text))

    def send_whatsapp_template(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language: LanguageTag,
        body_parameters: list[MessageText],
    ) -> None:
        self.attempts.append(ChannelKind.WHATSAPP)
        if ChannelKind.WHATSAPP in self.failing_channels:
            raise ExternalServiceError("The whatsapp channel is not connected.")

        self.templates.append(
            (
                business_id,
                channel_user_id,
                str(template_name),
                str(language),
                [str(parameter) for parameter in body_parameters],
            )
        )

    def send_whatsapp_template_in_language(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> None:
        raise AssertionError("Reminders follow the customer's language.")


class ReminderScene:
    """A Georgian restaurant with one table, its customer and the job."""

    def __init__(
        self,
        failing_channels: frozenset[ChannelKind] = frozenset(),
        reminder_lead: BookingReminderLeadSeconds | None = None,
        reminder_template: str | None = "booking_reminder",
    ) -> None:
        self.world = OperationsWorld()
        self.business: BusinessDocument = self.world.add_business()
        self.world.add_profile(self.business)
        self.table: ResourceDocument = self.world.add_resource(self.business, "Table 1")
        self.sender = RecordingChannelSender(failing_channels)
        self.reminders = SendBookingRemindersUseCase(
            business_repo=self.world.business_repo,
            business_profile_repo=self.world.profile_repo,
            booking_repo=self.world.booking_repo,
            resource_repo=self.world.resource_repo,
            contact_repo=self.world.contact_repo,
            conversation_repo=self.world.conversation_repo,
            message_repo=self.world.message_repo,
            channel_message_sender=self.sender,
            reminder_transformer=BookingReminderTransformer(LocalizedTextResolver()),
            reminder_template_transformer=BookingReminderTemplateTransformer(),
            wall_clock=self.world.clock.wall_clock,
            whatsapp_reminder_template=(
                None
                if reminder_template is None
                else WhatsAppTemplateName(reminder_template)
            ),
            **({} if reminder_lead is None else {"reminder_lead": reminder_lead}),
        )

    def customer_wrote(
        self,
        contact: ContactDocument,
        channel: ChannelKind,
        hours_ago: float,
        business: BusinessDocument | None = None,
    ) -> None:
        """The customer's last message in a channel, some hours before now."""

        moment = Microseconds(
            int(to_microseconds(DEFAULT_NOW)) - int(hours_ago * 3_600_000_000)
        )
        owner = business or self.business
        conversation = ConversationDocument(
            business_id=owner.id,
            contact_id=contact.id,
            assistant_version_id=AssistantVersionId(),
            channel=channel,
            channel_user_id=contact.channel_identities[0].channel_user_id,
            last_message_at=moment,
            created_at=moment,
            updated_at=moment,
        )
        self.world.conversation_repo.save(conversation)
        self.world.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=owner.id,
                direction=MessageDirection.INBOUND,
                author=MessageAuthor.CUSTOMER,
                text=MessageText("Hi"),
                created_at=moment,
                updated_at=moment,
            )
        )

    def add_customer(
        self,
        identities: dict[ChannelKind, str],
        language: str | None = "ka",
        business: BusinessDocument | None = None,
    ) -> ContactDocument:
        contact = self.world.add_contact(
            business or self.business,
            name="Nino",
            phone="+995555123456",
            language=language,
        )
        contact.channel_identities = [
            ChannelIdentity(channel=channel, channel_user_id=ChannelUserId(user_id))
            for channel, user_id in identities.items()
        ]
        self.world.contact_repo.save(contact)
        return contact

    def add_booking(
        self,
        contact: ContactDocument,
        starts: str,
        source_channel: ChannelKind = ChannelKind.WHATSAPP,
        status: BookingStatus = BookingStatus.CONFIRMED,
        is_sandbox: bool = False,
        business: BusinessDocument | None = None,
        resource: ResourceDocument | None = None,
    ) -> BookingDocument:
        starts_at = datetime.fromisoformat(starts)
        ends_at = starts_at.replace(hour=(starts_at.hour + 2) % 24)
        booking = self.world.add_booking(
            business or self.business,
            resource or self.table,
            contact,
            starts=starts_at.isoformat(),
            ends=ends_at.isoformat(),
            status=status,
            is_sandbox=is_sandbox,
        )
        booking.source_channel = source_channel
        self.world.booking_repo.save(booking)
        return booking

    def run(self) -> JobReport:
        return self.reminders.run(TICK)

    def stored(self, booking: BookingDocument) -> BookingDocument:
        stored = self.world.booking_repo.get(booking.business_id, booking.id)
        assert stored is not None
        return stored

    def usage_events(self) -> int:
        """Usage the job itself recorded (the channel sender meters sends)."""

        return len(
            self.world.usage_repo.list_by_business_between(
                self.business.id,
                to_microseconds(datetime.fromisoformat("2026-01-01T00:00:00+00:00")),
                to_microseconds(datetime.fromisoformat("2027-01-01T00:00:00+00:00")),
            )
        )


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


def test_a_cancellation_during_the_job_is_never_undone() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    first = scene.add_booking(
        contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM
    )
    second = scene.add_booking(
        contact, "2026-10-05T17:00:00+00:00", ChannelKind.TELEGRAM
    )

    def cancel_both_while_sending() -> None:
        for booking in (first, second):
            stored = scene.stored(booking)
            stored.status = BookingStatus.CANCELLED
            scene.world.booking_repo.save(stored)

    scene.sender.on_send = cancel_both_while_sending

    report = scene.run()

    # Only the first reminder was already on its way; the second booking is
    # read again before its turn and is no longer due.
    assert report.processed_count == 1
    assert len(scene.sender.sent) == 1
    for booking in (first, second):
        stored = scene.stored(booking)
        assert stored.status is BookingStatus.CANCELLED
        assert stored.reminder_sent_at is None


def test_a_move_during_the_send_keeps_the_new_time() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    booking = scene.add_booking(
        contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM
    )
    moved_start = BookingStartsAtUnixSeconds(int(booking.starts_at) + 3600)

    def move_while_sending() -> None:
        stored = scene.stored(booking)
        stored.starts_at = moved_start
        scene.world.booking_repo.save(stored)

    scene.sender.on_send = move_while_sending

    scene.run()

    stored = scene.stored(booking)
    assert stored.starts_at == moved_start
    assert stored.reminder_sent_at is None  # the next run reminds the new time


def test_a_second_run_does_not_remind_again() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    scene.add_booking(contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM)

    first = scene.run()
    second = scene.run()

    assert (first.processed_count, second.processed_count) == (1, 0)
    assert len(scene.sender.sent) == 1


def test_only_confirmed_real_bookings_starting_within_a_day_are_reminded() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    due = scene.add_booking(contact, "2026-10-06T07:00:00+00:00", ChannelKind.TELEGRAM)
    at_the_edge = scene.add_booking(
        contact, "2026-10-06T08:00:00+00:00", ChannelKind.TELEGRAM
    )
    skipped = [
        scene.add_booking(contact, "2026-10-06T08:00:01+00:00", ChannelKind.TELEGRAM),
        scene.add_booking(contact, "2026-10-05T07:00:00+00:00", ChannelKind.TELEGRAM),
        scene.add_booking(contact, "2026-10-05T08:00:00+00:00", ChannelKind.TELEGRAM),
        scene.add_booking(
            contact,
            "2026-10-05T15:00:00+00:00",
            ChannelKind.TELEGRAM,
            status=BookingStatus.CANCELLED,
        ),
        scene.add_booking(
            contact,
            "2026-10-05T15:00:00+00:00",
            ChannelKind.TELEGRAM,
            status=BookingStatus.PENDING,
        ),
        scene.add_booking(
            contact,
            "2026-10-05T15:00:00+00:00",
            ChannelKind.TELEGRAM,
            is_sandbox=True,
        ),
    ]

    report = scene.run()

    assert report.processed_count == 2
    assert scene.stored(due).reminder_sent_at is not None
    assert scene.stored(at_the_edge).reminder_sent_at is not None
    assert all(scene.stored(booking).reminder_sent_at is None for booking in skipped)


def test_reminder_lead_is_configurable() -> None:
    scene = ReminderScene(reminder_lead=BookingReminderLeadSeconds(2 * 60 * 60))
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    soon = scene.add_booking(contact, "2026-10-05T09:30:00+00:00", ChannelKind.TELEGRAM)
    later = scene.add_booking(
        contact, "2026-10-05T10:30:00+00:00", ChannelKind.TELEGRAM
    )

    scene.run()

    assert scene.stored(soon).reminder_sent_at is not None
    assert scene.stored(later).reminder_sent_at is None


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


@pytest.mark.parametrize(
    ("language", "expected_start"),
    [
        ("en", "Reminder: your booking at Salobie Bia"),
        ("ru", "Напоминание: ваша бронь в «Salobie Bia»"),
        ("ru-RU", "Напоминание: ваша бронь"),
        ("tr", "Reminder: your booking"),  # no Turkish text: English
        (None, "შეხსენება"),  # unknown language: the business default (ka)
    ],
)
def test_reminder_language_follows_the_customer(
    language: str | None,
    expected_start: str,
) -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"}, language=language)
    scene.add_booking(contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM)

    scene.run()

    [(_, _, _, text)] = scene.sender.sent
    assert str(text).startswith(expected_start)


def test_business_time_zone_of_another_country_is_used() -> None:
    scene = ReminderScene()
    rome = scene.world.add_business(
        name="Trattoria Roma",
        country_code="IT",
        timezone="Europe/Rome",
        currency_code="EUR",
        languages=("it", "en"),
        owner_language="it",
    )
    scene.world.add_profile(rome, cancellation_policy=None)
    table = scene.world.add_resource(rome, "Tavolo 1")
    contact = scene.add_customer(
        {ChannelKind.MESSENGER: "psid-1"}, language="en", business=rome
    )
    scene.customer_wrote(contact, ChannelKind.MESSENGER, hours_ago=5, business=rome)
    scene.add_booking(
        contact,
        "2026-10-05T18:00:00+00:00",
        ChannelKind.MESSENGER,
        business=rome,
        resource=table,
    )

    scene.run()

    [(business_id, channel, _, text)] = scene.sender.sent
    assert business_id == rome.id
    assert channel is ChannelKind.MESSENGER
    assert "Trattoria Roma" in str(text)
    assert "20:00" in str(text)  # 18:00 UTC is 20:00 in Rome (CEST)
    assert "Cancellation policy" not in str(text)


@pytest.mark.parametrize(
    ("status", "service_mode"),
    [
        (BusinessStatus.PAUSED, ServiceMode.FULL),
        (BusinessStatus.LIVE, ServiceMode.LEADS_ONLY),
    ],
)
def test_paused_or_leads_only_businesses_send_no_reminders(
    status: BusinessStatus,
    service_mode: ServiceMode,
) -> None:
    scene = ReminderScene()
    scene.business.status = status
    scene.business.service_mode = service_mode
    scene.world.business_repo.save(scene.business)
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    scene.add_booking(contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM)

    report = scene.run()

    assert report.processed_count == 0
    assert scene.sender.sent == []


def test_hotel_stay_reminder_names_the_check_in() -> None:
    scene = ReminderScene()
    hotel = scene.world.add_business(name="Old Tbilisi Hotel", niche_key=NicheKey.HOTEL)
    scene.world.add_profile(hotel, resource_kind=ResourceKind.ROOM, slot_minutes=1440)
    room = scene.world.add_resource(
        hotel,
        "Double room",
        kind=ResourceKind.ROOM,
        booking_unit=BookingUnit.NIGHT,
    )
    contact = scene.add_customer(
        {ChannelKind.TELEGRAM: "7001"}, language="en", business=hotel
    )
    scene.add_booking(
        contact,
        "2026-10-05T10:00:00+00:00",
        ChannelKind.TELEGRAM,
        business=hotel,
        resource=room,
    )

    scene.run()

    [(_, _, _, text)] = scene.sender.sent
    assert str(text).startswith("Reminder: your stay at Old Tbilisi Hotel")
    assert "check-in from 14:00" in str(text)


def test_rescheduled_booking_gets_a_new_reminder() -> None:
    scene = ReminderScene()
    contact = scene.add_customer({ChannelKind.TELEGRAM: "7001"})
    booking = scene.add_booking(
        contact, "2026-10-05T15:00:00+00:00", ChannelKind.TELEGRAM
    )
    scene.run()
    assert scene.stored(booking).reminder_sent_at is not None

    scene.world.reschedule_booking().run(
        RescheduleBookingCommand(
            business_id=scene.business.id,
            booking_id=booking.id,
            new_date=LocalDate("2026-10-06"),
            new_time=LocalTimeOfDay("18:00"),
            language=LanguageTag("en"),
        )
    )

    assert scene.stored(booking).reminder_sent_at is None
    assert scene.run().processed_count == 0  # 18:00 tomorrow is 30 hours away

    scene.world.clock.move_to(datetime.fromisoformat("2026-10-05T16:00:00+00:00"))

    assert scene.run().processed_count == 1
    assert len(scene.sender.sent) == 2


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


def build_message_input(
    language: str,
    unit: BookingUnit = BookingUnit.TIME_SLOT,
    policy: str | None = None,
) -> BookingMessageInput:
    return BookingMessageInput(
        business_name=BusinessName("Salobie Bia"),
        booking=BookingView(
            id=BookingId(),
            business_id=BusinessId(),
            resource_id=ResourceId(),
            resource_name=ResourceName("Table 1"),
            contact_id=ContactId(),
            contact_name=ContactName("Giorgi"),
            date=LocalDate("2026-10-06"),
            time=LocalTimeOfDay("19:30"),
            end_date=LocalDate("2026-10-06"),
            end_time=LocalTimeOfDay("21:30"),
            timezone=TimezoneName("Asia/Tbilisi"),
            party_size=PartySize(4),
            status=BookingStatus.CONFIRMED,
            source_channel=ChannelKind.WHATSAPP,
            created_at=Microseconds(1_790_000_000_000_000),
        ),
        booking_unit=unit,
        language=LanguageTag(language),
        cancellation_policy=None if policy is None else CancellationPolicyText(policy),
    )


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (
            "en",
            "Reminder: your booking at Salobie Bia is on Tuesday, October 6, 2026 "
            "at 19:30. Name: Giorgi. Guests: 4. To cancel or change it, just reply "
            "to this message.",
        ),
        (
            "ru",
            "Напоминание: ваша бронь в «Salobie Bia» — вторник, 6 октября "
            "2026\u202fг., 19:30. Имя: Giorgi. Гостей: 4. Чтобы отменить или "
            "перенести бронь, просто ответьте на это сообщение.",
        ),
    ],
)
def test_reminder_text(language: str, expected: str) -> None:
    transformer = BookingReminderTransformer(LocalizedTextResolver())

    text = transformer.transform(build_message_input(language))

    assert str(text) == expected


def test_reminder_text_in_georgian_with_the_cancellation_policy() -> None:
    transformer = BookingReminderTransformer(LocalizedTextResolver())

    text = str(
        transformer.transform(
            build_message_input("ka", policy="უფასო გაუქმება 2 საათით ადრე.")
        )
    )

    first_line, policy_line = text.split("\n")
    assert first_line.startswith("შეხსენება: თქვენი ჯავშანი Salobie Bia-ში")
    assert "19:30" in first_line
    assert policy_line == "გაუქმების წესები: უფასო გაუქმება 2 საათით ადრე."


def test_stay_reminder_text() -> None:
    transformer = BookingReminderTransformer(LocalizedTextResolver())

    text = str(transformer.transform(build_message_input("ru", BookingUnit.NIGHT)))

    assert text.startswith("Напоминание: ваше проживание в «Salobie Bia»")
    assert "заезд с 19:30" in text
