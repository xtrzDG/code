"""A business with managers and a customer conversation, ready for handoffs."""

from datetime import datetime

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import (
    HandoffReason,
    HandoffUrgency,
)
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.operations.builders import interval
from tests.operations.operations_world import OperationsWorld


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
        urgency: HandoffUrgency = HandoffUrgency.HIGH,
    ) -> HandoffResult:
        return self.world.handoff_to_human().run(
            HandoffCommand(
                business_id=self.business.id,
                conversation_id=conversation_id or self.conversation.id,
                contact_id=self.contact.id,
                reason=HandoffReason.COMPLAINT,
                summary=HandoffSummary("Tooth still hurts after the filling."),
                urgency=urgency,
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
