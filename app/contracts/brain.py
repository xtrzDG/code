"""Seams of the conversation engine ("brain") used across slices."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmToolDefinition
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest


class AssistantToolRegistryContract(RegistryContract, Protocol):
    def get(self, tool_name: AssistantToolName) -> LlmToolDefinition:
        """Definition with a strict JSON schema of the tool input."""
        raise NotImplementedError

    def list_definitions(
        self,
        tool_names: list[AssistantToolName],
    ) -> list[LlmToolDefinition]:
        """Definitions in the given order, without duplicates."""
        raise NotImplementedError


class MenuExtractionAdapterContract(AdapterContract, Protocol):
    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        """
        Read menu or price-list lines from a photo, PDF, text or web page.

        Raises:
            ExternalServiceError: the model or the page is unavailable.
            ValidationFailedError: the source cannot be read as a menu.
        """
        raise NotImplementedError
