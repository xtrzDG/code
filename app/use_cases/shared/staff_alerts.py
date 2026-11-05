"""
Building staff alerts in the use cases that raise them: what the alert is
about, the page its link opens, and its texts rendered once per language.
"""

from collections.abc import Callable

from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.constants.handoffs import HandoffUrgency
from app.schemas.constants.notifications import StaffAlertEvent, StaffLinkTarget
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.notifications.staff_alerts import StaffAlert, StaffAlertBrief
from app.schemas.typings.bookings.prefixed_id import LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import PushNotificationTag

URGENT_HANDOFFS: frozenset[HandoffUrgency] = frozenset(
    {HandoffUrgency.HIGH, HandoffUrgency.CRITICAL}
)


class StaffAlertTexts(StaffAlertTextsContract):
    """An alert's texts from two renderers, each language rendered once."""

    def __init__(
        self,
        detailed: Callable[[LanguageTag], MessageText],
        brief: Callable[[LanguageTag], StaffAlertBrief],
    ) -> None:
        self._render_detailed: Callable[[LanguageTag], MessageText] = detailed
        self._render_brief: Callable[[LanguageTag], StaffAlertBrief] = brief
        self._detailed: dict[LanguageTag, MessageText] = {}
        self._brief: dict[LanguageTag, StaffAlertBrief] = {}

    def detailed(self, language: LanguageTag) -> MessageText:
        if language not in self._detailed:
            self._detailed[language] = self._render_detailed(language)

        return self._detailed[language]

    def brief(self, language: LanguageTag) -> StaffAlertBrief:
        if language not in self._brief:
            self._brief[language] = self._render_brief(language)

        return self._brief[language]


def handoff_alert(
    business_id: BusinessId,
    handoff_id: HandoffId,
    conversation_id: ConversationId,
    urgency: HandoffUrgency,
) -> StaffAlert:
    """A handoff opens its conversation; high and critical ones are urgent."""

    return StaffAlert(
        business_id=business_id,
        event=StaffAlertEvent.HANDOFF,
        target=StaffLinkTarget.CONVERSATION,
        conversation_id=conversation_id,
        handoff_id=handoff_id,
        is_urgent=urgency in URGENT_HANDOFFS,
        tag=PushNotificationTag(f"handoff:{handoff_id}"),
    )


def lead_alert(
    business_id: BusinessId,
    lead_id: LeadId,
    conversation_id: ConversationId | None,
) -> StaffAlert:
    """A request opens the conversation it came from, else the requests."""

    return StaffAlert(
        business_id=business_id,
        event=StaffAlertEvent.LEAD,
        target=(
            StaffLinkTarget.LEAD
            if conversation_id is None
            else StaffLinkTarget.CONVERSATION
        ),
        conversation_id=conversation_id,
        lead_id=lead_id,
        tag=PushNotificationTag(f"lead:{lead_id}"),
    )


def booking_alert(booking: BookingView) -> StaffAlert:
    """A booking opens the bookings of its day; its changes share one tag."""

    return StaffAlert(
        business_id=booking.business_id,
        event=StaffAlertEvent.BOOKING,
        target=StaffLinkTarget.BOOKING,
        booking_id=booking.id,
        tag=PushNotificationTag(f"booking:{booking.id}"),
    )
