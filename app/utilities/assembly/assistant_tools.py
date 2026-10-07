"""Which tools an assistant version gets (concept section 4: by niche and channels)."""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument

BOOKING_TOOLS: frozenset[AssistantToolName] = frozenset(
    {
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
        AssistantToolName.CANCEL_BOOKING,
        AssistantToolName.RESCHEDULE_BOOKING,
        AssistantToolName.LIST_MY_BOOKINGS,
        AssistantToolName.JOIN_WAITLIST,
    }
)
# Tools the conversation offers by its channel (`select_available_tools`),
# never part of a version.
CONVERSATION_TOOLS: frozenset[AssistantToolName] = frozenset(
    {AssistantToolName.OFFER_CHOICES}
)


def can_take_bookings(
    profile: BusinessProfileDocument,
    resources: Sequence[ResourceDocument],
) -> bool:
    """A business books directly when it has booking rules and an active resource."""

    return profile.booking_rules is not None and any(
        resource.is_active for resource in resources
    )


def select_assistant_tools(
    takes_bookings: bool,
    has_links: bool,
) -> list[AssistantToolName]:
    """
    Every tool in declaration order, minus the booking tools for a business
    that does not book directly (it takes requests with create_lead instead)
    and minus send_link when the profile has no links to send. Tools a
    conversation adds by its channel (offer_choices) are not a version's.
    """

    return [
        tool_name
        for tool_name in AssistantToolName
        if tool_name not in CONVERSATION_TOOLS
        and (takes_bookings or tool_name not in BOOKING_TOOLS)
        and (has_links or tool_name is not AssistantToolName.SEND_LINK)
    ]
