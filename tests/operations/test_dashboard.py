from datetime import datetime

import pytest

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.bookings import BookingStatus, LeadType
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.dto.operations import DashboardStats, DashboardStatsQuery
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import HandoffSummary, UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.operations.builders import OperationsWorld
from tests.operations.fakes import to_microseconds


class DashboardFixture:
    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.business = self.world.add_business()
        self.world.add_profile(self.business)
        self.table = self.world.add_resource(self.business, "Table 4")
        self.contact = self.world.add_contact(self.business, "Giorgi")

    def conversation(
        self,
        created: str,
        channel: ChannelKind,
        language: str | None,
        is_sandbox: bool = False,
        is_after_hours: bool = False,
    ) -> ConversationDocument:
        return self.world.add_conversation(
            self.business,
            self.contact,
            channel,
            language=language,
            is_sandbox=is_sandbox,
            is_after_hours=is_after_hours,
            created_at=datetime.fromisoformat(created),
        )

    def message(
        self,
        conversation: ConversationDocument,
        created: str,
        author: MessageAuthor = MessageAuthor.CUSTOMER,
    ) -> None:
        moment = to_microseconds(datetime.fromisoformat(created))
        self.world.message_repo.save(
            MessageDocument(
                conversation_id=conversation.id,
                business_id=self.business.id,
                direction=(
                    MessageDirection.INBOUND
                    if author is MessageAuthor.CUSTOMER
                    else MessageDirection.OUTBOUND
                ),
                author=author,
                text=MessageText("Hello"),
                created_at=moment,
                updated_at=moment,
            )
        )

    def booking(
        self,
        created: str,
        status: BookingStatus = BookingStatus.CONFIRMED,
        is_sandbox: bool = False,
    ) -> None:
        moment = to_microseconds(datetime.fromisoformat(created))
        self.world.booking_repo.save(
            BookingDocument(
                business_id=self.business.id,
                resource_id=self.table.id,
                contact_id=self.contact.id,
                starts_at=BookingStartsAtUnixSeconds(1_791_000_000),
                ends_at=BookingEndsAtUnixSeconds(1_791_007_200),
                party_size=PartySize(2),
                status=status,
                source_channel=ChannelKind.WHATSAPP,
                is_sandbox=is_sandbox,
                created_at=moment,
                updated_at=moment,
            )
        )

    def handoff(
        self,
        conversation: ConversationDocument,
        created: str,
        reason: HandoffReason,
        urgency: HandoffUrgency,
        is_sandbox: bool = False,
    ) -> None:
        moment = to_microseconds(datetime.fromisoformat(created))
        self.world.handoff_repo.save(
            HandoffDocument(
                business_id=self.business.id,
                conversation_id=conversation.id,
                contact_id=self.contact.id,
                reason=reason,
                summary=HandoffSummary("Needs a person"),
                urgency=urgency,
                is_sandbox=is_sandbox,
                created_at=moment,
                updated_at=moment,
            )
        )

    def usage(
        self,
        created: str,
        seconds: int,
        conversation: ConversationDocument | None = None,
        kind: UsageKind = UsageKind.VOICE_SECONDS,
    ) -> None:
        self.world.usage_repo.append(
            UsageEventDocument(
                business_id=self.business.id,
                conversation_id=None if conversation is None else conversation.id,
                kind=kind,
                quantity=UsageQuantity(seconds),
                occurred_at=to_microseconds(datetime.fromisoformat(created)),
            )
        )

    def stats(
        self,
        date_from: str | None = "2026-10-01",
        date_to: str | None = "2026-10-05",
    ) -> DashboardStats:
        return self.world.dashboard().run(
            DashboardStatsQuery(
                business_id=self.business.id,
                date_from=None if date_from is None else LocalDate(date_from),
                date_to=None if date_to is None else LocalDate(date_to),
            )
        )


def test_dashboard_counts_the_period_in_the_business_time_zone() -> None:
    dashboard = DashboardFixture()
    in_hours = dashboard.conversation(
        "2026-10-02T13:00:00+04:00", ChannelKind.WHATSAPP, "ka"
    )
    at_night = dashboard.conversation(
        "2026-10-03T02:00:00+04:00", ChannelKind.TELEGRAM, "ru"
    )
    dashboard.conversation(
        "2026-10-04T15:00:00+04:00", ChannelKind.PHONE, "en", is_after_hours=True
    )
    # 00:30 local on Oct 1 is still Sep 30 in UTC, but inside the period.
    dashboard.conversation("2026-10-01T00:30:00+04:00", ChannelKind.WHATSAPP, None)
    sandbox = dashboard.conversation(
        "2026-10-02T13:00:00+04:00", ChannelKind.OWNER_TEST, "en", is_sandbox=True
    )
    dashboard.conversation("2026-09-20T13:00:00+04:00", ChannelKind.WHATSAPP, "ka")
    dashboard.message(in_hours, "2026-10-02T13:00:00+04:00")
    dashboard.message(in_hours, "2026-10-02T13:01:00+04:00")
    dashboard.message(in_hours, "2026-10-02T13:00:30+04:00", MessageAuthor.ASSISTANT)
    dashboard.message(at_night, "2026-10-03T02:00:00+04:00")
    dashboard.message(sandbox, "2026-10-02T13:00:00+04:00")
    dashboard.message(at_night, "2026-10-06T02:00:00+04:00")
    dashboard.booking("2026-10-02T13:05:00+04:00")
    dashboard.booking("2026-10-03T02:05:00+04:00")
    dashboard.booking("2026-10-04T15:05:00+04:00", BookingStatus.CANCELLED)
    dashboard.booking("2026-10-04T15:05:00+04:00", is_sandbox=True)
    dashboard.booking("2026-09-04T15:05:00+04:00")
    dashboard.handoff(
        at_night,
        "2026-10-03T02:10:00+04:00",
        HandoffReason.COMPLAINT,
        HandoffUrgency.HIGH,
    )
    dashboard.handoff(
        in_hours,
        "2026-10-02T13:10:00+04:00",
        HandoffReason.COMPLAINT,
        HandoffUrgency.NORMAL,
    )
    dashboard.handoff(
        in_hours,
        "2026-10-02T13:20:00+04:00",
        HandoffReason.CUSTOMER_REQUEST,
        HandoffUrgency.NORMAL,
    )
    dashboard.handoff(
        sandbox,
        "2026-10-02T13:20:00+04:00",
        HandoffReason.EMERGENCY,
        HandoffUrgency.CRITICAL,
        is_sandbox=True,
    )
    for is_sandbox in (False, True):
        moment = to_microseconds(datetime.fromisoformat("2026-10-02T13:00:00+04:00"))
        dashboard.world.lead_repo.save(
            LeadDocument(
                business_id=dashboard.business.id,
                contact_id=dashboard.contact.id,
                lead_type=LeadType.BANQUET,
                details=LeadDetails("Wedding"),
                source_channel=ChannelKind.WHATSAPP,
                is_sandbox=is_sandbox,
                created_at=moment,
                updated_at=moment,
            )
        )

    for text, is_resolved, is_sandbox in (
        ("Parking?", False, False),
        ("Wi-Fi?", False, False),
        ("Vegan?", True, False),
        ("Kids menu?", False, True),
    ):
        dashboard.world.question_repo.save(
            UnansweredQuestionDocument(
                business_id=dashboard.business.id,
                question=UnansweredQuestionText(text),
                language=LanguageTag("en"),
                last_seen_at=dashboard.world.clock.now_microseconds(),
                is_resolved=is_resolved,
                is_sandbox=is_sandbox,
            )
        )

    dashboard.usage("2026-10-02T13:00:00+04:00", 90, in_hours)
    dashboard.usage("2026-10-03T02:00:00+04:00", 45)
    dashboard.usage("2026-10-02T13:00:00+04:00", 600, sandbox)
    dashboard.usage("2026-10-02T13:00:00+04:00", 5000, kind=UsageKind.LLM_INPUT_TOKENS)
    dashboard.usage("2026-09-02T13:00:00+04:00", 600)

    stats = dashboard.stats()

    assert (stats.date_from, stats.date_to, stats.timezone) == (
        "2026-10-01",
        "2026-10-05",
        "Asia/Tbilisi",
    )
    assert stats.conversation_count == 4
    assert stats.customer_message_count == 3
    assert stats.after_hours_conversation_count == 3
    assert stats.after_hours_share_percent == 75.0
    assert stats.booking_count == 3
    assert [(item.status, item.count) for item in stats.bookings_by_status] == [
        (BookingStatus.CONFIRMED, 2),
        (BookingStatus.CANCELLED, 1),
    ]
    assert stats.lead_count == 1
    assert stats.handoff_count == 3
    assert [(item.reason, item.count) for item in stats.handoffs_by_reason] == [
        (HandoffReason.COMPLAINT, 2),
        (HandoffReason.CUSTOMER_REQUEST, 1),
    ]
    assert [(item.urgency, item.count) for item in stats.handoffs_by_urgency] == [
        (HandoffUrgency.NORMAL, 2),
        (HandoffUrgency.HIGH, 1),
    ]
    assert [(item.language, item.count) for item in stats.languages] == [
        ("en", 1),
        ("ka", 1),
        ("ru", 1),
    ]
    assert [(item.channel, item.count) for item in stats.channels] == [
        (ChannelKind.WHATSAPP, 2),
        (ChannelKind.PHONE, 1),
        (ChannelKind.TELEGRAM, 1),
    ]
    assert stats.open_unanswered_question_count == 2
    assert stats.used_voice_minutes == 3


def test_empty_dashboard_defaults_to_the_last_thirty_days() -> None:
    dashboard = DashboardFixture()

    stats = dashboard.stats(date_from=None, date_to=None)

    assert (stats.date_from, stats.date_to) == ("2026-09-06", "2026-10-05")
    assert stats.conversation_count == 0
    assert stats.after_hours_share_percent == 0.0
    assert stats.bookings_by_status == []
    assert stats.used_voice_minutes == 0


def test_invalid_periods_are_refused() -> None:
    dashboard = DashboardFixture()

    with pytest.raises(ValidationFailedError, match="after the end"):
        dashboard.stats("2026-10-05", "2026-10-01")

    with pytest.raises(ValidationFailedError, match="366 days"):
        dashboard.stats("2025-01-01", "2026-10-01")


def test_without_opening_hours_only_flagged_conversations_are_after_hours() -> None:
    dashboard = DashboardFixture()
    profile = dashboard.world.profile_repo.get_by_business(dashboard.business.id)
    assert profile is not None
    profile.hours = []
    dashboard.world.profile_repo.save(profile)
    dashboard.conversation("2026-10-03T02:00:00+04:00", ChannelKind.WHATSAPP, "ka")
    dashboard.conversation(
        "2026-10-03T03:00:00+04:00",
        ChannelKind.WHATSAPP,
        "ka",
        is_after_hours=True,
    )
    dashboard.conversation("2026-10-03T04:00:00+04:00", ChannelKind.WHATSAPP, "ka")

    stats = dashboard.stats()

    assert stats.after_hours_conversation_count == 1
    assert stats.after_hours_share_percent == 33.3
