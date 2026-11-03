"""Which model tools a conversation offers."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import ServiceMode
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.utilities.channels.voice_service import CALLER_ID_BOUND_TOOLS

# Tools offered while bookings are paused (unpaid subscription past grace):
# taking a request, passing to staff, searching the knowledge base, telling
# a customer about the bookings they already have, and a caller's refusal
# of the recording or request for its transcript (never a paid feature).
LEADS_ONLY_TOOLS: frozenset[AssistantToolName] = frozenset(
    {
        AssistantToolName.CREATE_LEAD,
        AssistantToolName.HANDOFF_TO_HUMAN,
        AssistantToolName.SEARCH_KNOWLEDGE,
        AssistantToolName.LIST_MY_BOOKINGS,
        AssistantToolName.OFFER_CHOICES,
        AssistantToolName.DECLINE_RECORDING,
        AssistantToolName.SEND_CALL_TRANSCRIPT,
    }
)
# Channels without anything to tap: a call is spoken.
CHANNELS_WITHOUT_CHOICES: frozenset[ChannelKind] = frozenset({ChannelKind.PHONE})
# Only a call is recorded, so only a caller can decline the recording or
# ask for its transcript.
RECORDED_CHANNELS: frozenset[ChannelKind] = frozenset({ChannelKind.PHONE})

# A version that makes bookings or requests may ask their deposits.
DEPOSIT_TAKING_TOOLS: frozenset[AssistantToolName] = frozenset(
    {AssistantToolName.CREATE_BOOKING, AssistantToolName.CREATE_LEAD}
)
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
    The version's tools in its order (with list_my_bookings, join_waitlist
    and send_link for a version assembled before it had them), then, in a
    chat channel, offer_choices (every version gets it, so options to tap
    need no new version) and send_payment_link for a version that books or
    takes requests (a deposit's link is written, never spoken), and on a
    call decline_recording and send_call_transcript; in LEADS_ONLY mode
    only the tools of LEADS_ONLY_TOOLS remain.
    """

    tools: list[AssistantToolName] = with_send_link(
        with_join_waitlist(with_list_my_bookings(list(version.tools)))
    )
    if channel in RECORDED_CHANNELS:
        tools = with_call_tools(tools)
    if (
        channel not in CHANNELS_WITHOUT_CHOICES
        and AssistantToolName.OFFER_CHOICES not in tools
    ):
        tools.append(AssistantToolName.OFFER_CHOICES)
    if (
        channel not in CHANNELS_WITHOUT_CHOICES
        and AssistantToolName.SEND_PAYMENT_LINK not in tools
        and DEPOSIT_TAKING_TOOLS & set(tools)
    ):
        tools.append(AssistantToolName.SEND_PAYMENT_LINK)
    if business.service_mode is ServiceMode.LEADS_ONLY:
        return [tool for tool in tools if tool in LEADS_ONLY_TOOLS]

    return tools


def select_voice_agent_tools(
    version: AssistantVersionDocument,
) -> list[AssistantToolName]:
    """
    The tools the business's voice agent is built with: the version's, with
    join_waitlist and send_link for a version assembled before it had them
    and the call tools (decline_recording, send_call_transcript), but none
    of CALLER_ID_BOUND_TOOLS (list_my_bookings, cancel_booking,
    reschedule_booking): a caller id proves nobody's identity, so the agent
    is not even given them (the tool webhook still refuses them). The
    service mode is not applied: it changes without a new agent, and every
    tool call is checked against the conversation's tools when it comes in.
    """

    return [
        tool
        for tool in with_call_tools(
            with_send_link(with_join_waitlist(list(version.tools)))
        )
        if tool not in CALLER_ID_BOUND_TOOLS
    ]


# Tools every call offers, last and in this order: no version stores them.
CALL_TOOLS: tuple[AssistantToolName, ...] = (
    AssistantToolName.DECLINE_RECORDING,
    AssistantToolName.SEND_CALL_TRANSCRIPT,
)


def with_call_tools(
    tools: list[AssistantToolName],
) -> list[AssistantToolName]:
    """Every call offers decline_recording and send_call_transcript, last."""

    return [*tools, *(tool for tool in CALL_TOOLS if tool not in tools)]


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


def with_send_link(tools: list[AssistantToolName]) -> list[AssistantToolName]:
    """
    Every version can send a link: every business has its privacy notice,
    its own or else the platform's hosted one, whose link a call's greeting
    offers to every caller (VOICE-05). One assembled without links gets
    send_link where a new version has it, without the owner publishing
    again.
    """

    if AssistantToolName.SEND_LINK in tools:
        return tools

    order: list[AssistantToolName] = list(AssistantToolName)
    position: int = sum(
        1
        for tool in tools
        if order.index(tool) < order.index(AssistantToolName.SEND_LINK)
    )
    return [*tools[:position], AssistantToolName.SEND_LINK, *tools[position:]]
