from app.contracts.brain import AssistantToolRegistryContract
from app.registries.tools.assistant_tool_catalog import build_tool_definitions
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmToolDefinition


class AssistantToolRegistry(AssistantToolRegistryContract):
    """
    Definitions of the model tools (concept section 5) with strict JSON
    schemas. Definitions are built once and are byte-identical across calls,
    so the provider's prompt cache keeps working.
    """

    def __init__(self) -> None:
        self._definitions: dict[AssistantToolName, LlmToolDefinition] = (
            build_tool_definitions()
        )

    def get(self, tool_name: AssistantToolName) -> LlmToolDefinition:
        return self._definitions[tool_name]

    def list_definitions(
        self,
        tool_names: list[AssistantToolName],
    ) -> list[LlmToolDefinition]:
        definitions: list[LlmToolDefinition] = []
        for tool_name in tool_names:
            definition: LlmToolDefinition = self._definitions[tool_name]
            if definition not in definitions:
                definitions.append(definition)

        return definitions
