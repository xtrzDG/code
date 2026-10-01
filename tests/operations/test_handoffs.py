from datetime import datetime

import pytest

from app.facilitators.staff.manager_broadcast_facilitator import (
    ManagerBroadcastFacilitator,
)
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffStatus,
    HandoffUrgency,
)
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.operations import ListHandoffsQuery, ResolveHandoffCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from tests.operations.builders import OperationsWorld, every_day, interval
from tests.operations.fakes import RecordingManagerNotifier


class HandoffFixture:
    """Jerusalem clinic open Sunday to Thursday 09:00-18:00."""

    def __init__(self, now: str, with_hours: bool = True) -> None:
        self.world = OperationsWorld(datetime.fromisoformat(now))
        self.business = self.world.add_business(
            name="Tel Aviv Smile",
            country_code="IL",
            timezone="Asia/Jerusalem",
            currency_code="ILS",
            languages=("he", "ar", "en", "ru"),
            owner_language="he",
        )
        if with_hours:
            self.world.add_profile(
                self.business,
                hours=[
                    interval(weekday, "09:00", "18:00")
                    for weekday in (
                        Weekday.SUNDAY,
                        Weekday.MONDAY,
                        Weekday.TUESDAY,
                        Weekday.WEDNESDAY,
                        Weekday.THURSDAY,
                    )
                ],
            )

        self.contact = self.world.add_contact(self.business, "Yossi", "+972502345678")
        self.conversation: ConversationDocument = self.world.add_conversation(
            self.business, self.contact, ChannelKind.TELEGRAM, language="he"
        )

    def hand_off(
        self,
        language: str = "he",
        is_sandbox: bool = False,
        conversation_id: ConversationId | None = None,
    ) -> HandoffResult:
        return self.world.handoff_to_human().run(
            HandoffCommand(
                business_id=self.business.id,
                conversation_id=conversation_id or self.conversation.id,
                contact_id=self.contact.id,
                reason=HandoffReason.COMPLAINT,
                summary=HandoffSummary("Tooth still hurts after the filling."),
                urgency=HandoffUrgency.HIGH,
                source_channel=ChannelKind.TELEGRAM,
                language=LanguageTag(language),
                is_sandbox=is_sandbox,
            )
        )

    def conversation_status(self) -> ConversationStatus:
        conversation = self.world.conversation_repo.get(
            self.business.id, self.conversation.id
        )
        assert conversation is not None
        return conversation.status


def test_handoff_in_opening_hours_notifies_staff_and_silences_the_bot() -> None:
    # Monday 11:00 in Jerusalem.
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")

    result = fixture.hand_off(language="ar")

    assert result.status is HandoffStatus.NOTIFIED
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
    assert texts["en"].startswith("[High] A customer needs a person")


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
    fixture.world.broadcaster = ManagerBroadcastFacilitator(fixture.world.notifier)

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


def test_resolving_reopens_the_conversation_after_the_last_open_handoff() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    first = fixture.hand_off()
    second = fixture.hand_off()
    resolve = fixture.world.resolve_handoff()

    resolved_first = resolve.run(
        ResolveHandoffCommand(business_id=fixture.business.id, handoff_id=first.id)
    )
    assert resolved_first.status is HandoffStatus.RESOLVED
    assert resolved_first.resolved_at is not None
    assert fixture.conversation_status() is ConversationStatus.HANDOFF

    fixture.world.clock.move_to(datetime.fromisoformat("2026-10-05T12:00:00+03:00"))
    resolved_second = resolve.run(
        ResolveHandoffCommand(business_id=fixture.business.id, handoff_id=second.id)
    )
    assert fixture.conversation_status() is ConversationStatus.OPEN
    assert resolved_second.contact_phone_number == "+972502345678"

    again = resolve.run(
        ResolveHandoffCommand(business_id=fixture.business.id, handoff_id=second.id)
    )
    assert again.resolved_at == resolved_second.resolved_at
    with pytest.raises(NotFoundError):
        resolve.run(
            ResolveHandoffCommand(
                business_id=fixture.business.id, handoff_id=HandoffId()
            )
        )


def test_list_handoffs_filters_and_audits() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    fixture.hand_off()
    fixture.hand_off(is_sandbox=True)
    staff_id = UserId()

    real = fixture.world.list_handoffs().run(
        ListHandoffsQuery(business_id=fixture.business.id, actor_id=staff_id)
    )
    pending = fixture.world.list_handoffs().run(
        ListHandoffsQuery(
            business_id=fixture.business.id,
            actor_id=staff_id,
            status=HandoffStatus.PENDING,
            include_sandbox=True,
        )
    )

    assert [item.status for item in real.items] == [HandoffStatus.NOTIFIED]
    assert real.items[0].contact_name == "Yossi"
    assert real.items[0].urgency is HandoffUrgency.HIGH
    assert len(pending.items) == 1 and pending.items[0].is_sandbox
    assert len(fixture.world.audit_repo.list_by_business(fixture.business.id)) == 2


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
