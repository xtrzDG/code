"""Handing a conversation to a human: notices, promised reply times, failures."""

from datetime import datetime

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.dto.handoffs import HandoffCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.operations.builders import every_day
from tests.operations.fakes import RecordingManagerNotifier
from tests.operations.handoff_fixture import HandoffFixture
from tests.operations.operations_world import OperationsWorld


def test_handoff_in_opening_hours_notifies_staff_and_silences_the_bot() -> None:
    # Monday 11:00 in Jerusalem.
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")

    result = fixture.hand_off(language="ar")

    # Queued for every staff contact; delivery marks it NOTIFIED later.
    assert result.status is HandoffStatus.PENDING
    assert str(result.customer_message) == (
        "تم تحويل طلبك إلى أحد الزملاء. سيتم الرد عليك قريبًا."
    )
    assert fixture.conversation_status() is ConversationStatus.HANDOFF
    texts = {
        str(contact.language): str(text)
        for contact, text in fixture.world.notifier.sent
    }
    assert texts["ru"].splitlines() == [
        "[Высокая] Клиенту нужен человек · Tel Aviv Smile",
        "Причина: Жалоба",
        "Tooth still hurts after the filling.",
        "Имя: Yossi",
        "Телефон: +972 50-234-5678",
        "Канал: Telegram",
    ]
    assert texts["ka"].startswith("[მაღალი] კლიენტს ადამიანი სჭირდება")
    # E-mail gets the brief: urgency and reason, no summary, name or phone.
    assert texts["en"] == (
        "Urgent: a customer needs a person\nTel Aviv Smile · Complaint"
    )


def test_handoff_after_hours_promises_a_reply_when_the_business_opens() -> None:
    # Friday evening: the clinic reopens on Sunday at 09:00.
    fixture = HandoffFixture("2026-10-09T20:00:00+03:00")

    hebrew = fixture.hand_off(language="he")
    english = fixture.hand_off(language="en")
    russian = fixture.hand_off(language="ru")

    assert str(english.customer_message) == (
        "Your request has been passed to a colleague. We are closed now; they will "
        "reply when we open: Sunday, October 11, 2026, 09:00."
    )
    assert "воскресенье, 11 октября 2026" in str(russian.customer_message)
    assert "09:00" in str(hebrew.customer_message)
    assert "כשנפתח" in str(hebrew.customer_message)


def test_handoff_without_known_hours_says_soon() -> None:
    fixture = HandoffFixture("2026-10-09T20:00:00+03:00", with_hours=False)

    result = fixture.hand_off(language="en")

    assert str(result.customer_message) == (
        "Your request has been passed to a colleague. They will reply soon."
    )


def test_failed_delivery_and_no_managers_mark_the_handoff() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    fixture.world.notifier = RecordingManagerNotifier(
        failing_addresses=frozenset({"4242", "+995555000111", "anna@example.com"})
    )
    fixture.world.rebuild_staff_alerts()

    assert fixture.hand_off().status is HandoffStatus.NOTIFICATION_FAILED

    business = fixture.world.business_repo.get(fixture.business.id)
    assert business is not None
    business.manager_contacts = []
    fixture.world.business_repo.save(business)
    assert fixture.hand_off().status is HandoffStatus.NOTIFICATION_FAILED


def test_sandbox_handoff_stays_pending_and_unknown_conversation_fails() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")

    result = fixture.hand_off(is_sandbox=True)

    assert result.status is HandoffStatus.PENDING
    assert fixture.world.notifier.sent == []
    assert fixture.conversation_status() is ConversationStatus.HANDOFF
    with pytest.raises(NotFoundError):
        fixture.hand_off(conversation_id=ConversationId())


def test_overnight_business_is_open_after_midnight() -> None:
    # Tbilisi bar open every day 18:00-03:00; 01:30 on Tuesday is open time.
    world = OperationsWorld(datetime.fromisoformat("2026-10-06T01:30:00+04:00"))
    bar = world.add_business(name="Bar 33")
    world.add_profile(bar, hours=every_day("18:00", "03:00"))
    contact = world.add_contact(bar, "Dato")
    conversation = world.add_conversation(bar, contact)

    result = world.handoff_to_human().run(
        HandoffCommand(
            business_id=bar.id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            reason=HandoffReason.CUSTOMER_REQUEST,
            summary=HandoffSummary("Wants to talk to the manager."),
            urgency=HandoffUrgency.NORMAL,
            source_channel=ChannelKind.WHATSAPP,
            language=LanguageTag("ka"),
        )
    )

    assert str(result.customer_message) == (
        "თქვენი მოთხოვნა კოლეგას გადაეცა. მალე გიპასუხებენ."
    )
