"""A business with conversations, bookings, leads and usage for dashboard tests."""

from datetime import datetime

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.operations.dashboard import DashboardStats, DashboardStatsQuery
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import HandoffSummary
from tests.operations.fakes import to_microseconds
from tests.operations.operations_world import OperationsWorld


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
