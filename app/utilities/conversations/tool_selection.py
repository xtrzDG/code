"""Which model tools a conversation offers."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument

# Tools offered while bookings are paused (unpaid subscription past grace):
# taking a request, passing to staff, searching the knowledge base, and
# telling a customer about the bookings they already have.
LEADS_ONLY_TOOLS: frozenset[AssistantToolName] = frozenset(
    {
        AssistantToolName.CREATE_LEAD,
        AssistantToolName.HANDOFF_TO_HUMAN,
        AssistantToolName.SEARCH_KNOWLEDGE,
        AssistantToolName.LIST_MY_BOOKINGS,
        AssistantToolName.OFFER_CHOICES,
    }
)
# Channels without anything to tap: a call is spoken.
CHANNELS_WITHOUT_CHOICES: frozenset[ChannelKind] = frozenset({ChannelKind.PHONE})

# The booking tools join_waitlist follows in a version's list.
BOOKING_TOOL_ORDER: frozenset[AssistantToolName] = frozenset(
    {
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
        AssistantToolName.CANCEL_BOOKING,
        AssistantToolName.RESCHEDULE_BOOKING,
        AssistantToolName.LIST_MY_BOOKINGS,
    }
)


def select_available_tools(
    version: AssistantVersionDocument,
    business: BusinessDocument,
    channel: ChannelKind = ChannelKind.PHONE,
) -> list[AssistantToolName]:
    """
    The version's tools in its order (with list_my_bookings and
    join_waitlist for a version assembled before they existed), then
    offer_choices in a chat channel (every version gets it, so options to
    tap need no new version); in LEADS_ONLY mode only the tools of
    LEADS_ONLY_TOOLS remain.
    """

    tools: list[AssistantToolName] = with_join_waitlist(
        with_list_my_bookings(list(version.tools))
    )
    if (
        channel not in CHANNELS_WITHOUT_CHOICES
        and AssistantToolName.OFFER_CHOICES not in tools
    ):
        tools.append(AssistantToolName.OFFER_CHOICES)
    if business.service_mode is ServiceMode.LEADS_ONLY:
        return [tool for tool in tools if tool in LEADS_ONLY_TOOLS]

    return tools


def with_list_my_bookings(
    tools: list[AssistantToolName],
) -> list[AssistantToolName]:
    """
    A version that can change bookings can also list them: one assembled
    before list_my_bookings existed gets it right after its booking tools,
    where a new version has it, so its customers can ask about their
    bookings without the owner publishing again.
    """

    if (
        AssistantToolName.CANCEL_BOOKING not in tools
        or AssistantToolName.LIST_MY_BOOKINGS in tools
    ):
        return tools

    anchor: AssistantToolName = (
        AssistantToolName.RESCHEDULE_BOOKING
        if AssistantToolName.RESCHEDULE_BOOKING in tools
        else AssistantToolName.CANCEL_BOOKING
    )
    position: int = tools.index(anchor) + 1
    return [*tools[:position], AssistantToolName.LIST_MY_BOOKINGS, *tools[position:]]


def with_join_waitlist(tools: list[AssistantToolName]) -> list[AssistantToolName]:
    """
    A version that checks availability can also put a customer on the
    waitlist: one assembled before join_waitlist existed gets it right after
    its booking tools, where a new version has it, so a business that turns
    its waitlist on needs no new version (the tool answers that the list is
    off otherwise, and availability offers it only when it is on).
    """

    if (
        AssistantToolName.CHECK_AVAILABILITY not in tools
        or AssistantToolName.JOIN_WAITLIST in tools
    ):
        return tools

    position: int = 1 + max(
        tools.index(tool) for tool in tools if tool in BOOKING_TOOL_ORDER
    )
    return [*tools[:position], AssistantToolName.JOIN_WAITLIST, *tools[position:]]
