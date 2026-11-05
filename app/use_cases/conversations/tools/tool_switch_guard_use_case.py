from app.contracts.platform_safety import PlatformPauseRepoContract
from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.dto.assistant_tools import (
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.use_cases.conversations.tools.tool_outcomes import error_outcome
from app.utilities.conversations.tool_switches import SWITCHED_OFF_RESULT


class ToolSwitchGuardUseCase(
    UseCaseContract[AssistantToolInvocation, AssistantToolOutcome]
):
    """
    Runs a tool call of the model only while its tool is switched on (AI-10):
    an owner may switch actions off for the business (Settings → General,
    `AssistantSettingsDocument.disabled_tools`) and a platform admin for
    every business (`PlatformPauseDocument.disabled_tools`). A switched-off
    call never runs: the model gets an error result that points it to a
    request or a colleague. Every tool call, in a chat or on a call, comes
    through here, so a switch holds from the next call on.
    """

    def __init__(
        self,
        run_assistant_tool: UseCaseContract[
            AssistantToolInvocation, AssistantToolOutcome
        ],
        assistant_settings_repo: AssistantSettingsRepoContract,
        platform_pause_repo: PlatformPauseRepoContract,
    ) -> None:
        self._run_assistant_tool: UseCaseContract[
            AssistantToolInvocation, AssistantToolOutcome
        ] = run_assistant_tool
        self._assistant_settings_repo: AssistantSettingsRepoContract = (
            assistant_settings_repo
        )
        self._platform_pause_repo: PlatformPauseRepoContract = platform_pause_repo

    def run(self, input_data: AssistantToolInvocation) -> AssistantToolOutcome:
        tool: AssistantToolName = input_data.call.tool_name
        if tool in self._switched_off(input_data):
            return error_outcome(
                input_data.call, SWITCHED_OFF_RESULT.format(tool=str(tool))
            )

        return self._run_assistant_tool.run(input_data)

    def _switched_off(
        self, input_data: AssistantToolInvocation
    ) -> frozenset[AssistantToolName]:
        settings: AssistantSettingsDocument | None = (
            self._assistant_settings_repo.get_by_business(
                input_data.context.business_id
            )
        )
        platform: PlatformPauseDocument | None = self._platform_pause_repo.get()
        return frozenset(
            [
                *([] if settings is None else settings.disabled_tools),
                *([] if platform is None else platform.disabled_tools),
            ]
        )
