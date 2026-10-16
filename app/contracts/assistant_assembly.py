"""Seams the assistant assembly needs from the conversation engine."""

from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmToolDefinition


class AssistantToolCatalogContract(RegistryContract, Protocol):
    """
    Tool definitions (description and JSON Schema of the arguments) exactly as
    the chat offers them to the language model, so the voice agent assembled
    from the same version calls the same tools (concept section 4).
    """

    def list_definitions(
        self,
        tool_names: list[AssistantToolName],
    ) -> list[LlmToolDefinition]:
        """Definitions of the given tools, in the given order."""
        raise NotImplementedError
