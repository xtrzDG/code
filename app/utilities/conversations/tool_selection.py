"""Which model tools a conversation offers."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import ServiceMode
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument

# Tools offered while bookings are paused (unpaid subscription past grace).
LEADS_ONLY_TOOLS: frozenset[AssistantToolName] = frozenset(
    {
        AssistantToolName.CREATE_LEAD,
        AssistantToolName.HANDOFF_TO_HUMAN,
        AssistantToolName.SEARCH_KNOWLEDGE,
    }
)


def select_available_tools(
    version: AssistantVersionDocument,
    business: BusinessDocument,
) -> list[AssistantToolName]:
    """
    The version's tools in its order; in LEADS_ONLY mode only taking a
    request, passing to staff and searching the knowledge base remain.
    """

    if business.service_mode is ServiceMode.LEADS_ONLY:
        return [tool for tool in version.tools if tool in LEADS_ONLY_TOOLS]

    return list(version.tools)
