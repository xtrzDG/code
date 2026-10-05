"""Which model tools a conversation offers."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import ServiceMode
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
    }
)


def select_available_tools(
    version: AssistantVersionDocument,
    business: BusinessDocument,
) -> list[AssistantToolName]:
    """
    The version's tools in its order (with list_my_bookings for a version
    assembled before it existed); in LEADS_ONLY mode only the tools of
    LEADS_ONLY_TOOLS remain.
    """

    tools: list[AssistantToolName] = with_list_my_bookings(list(version.tools))
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
