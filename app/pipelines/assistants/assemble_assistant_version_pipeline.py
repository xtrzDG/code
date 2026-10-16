from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssistantVersionQuery,
    RunAutotestsCommand,
)
from app.schemas.dto.assistants.assistant_views import (
    AssistantVersionDetails,
    AutotestRunView,
)


class AssembleAssistantVersionPipeline(
    PipelineContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
):
    """
    Assembly phase followed by the autotest phase (concept section 4).

    The version is assembled first; unless the owner turned it off, its
    autotests are started (in the requested languages and kinds), and the
    version is returned as it stands afterwards: TESTING while the worker
    plays a queued run, READY or TESTS_FAILED after a run played in place,
    or DRAFT when tests were skipped.
    """

    def __init__(
        self,
        assemble_assistant_version: OrchestratorContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ],
        run_autotests: OrchestratorContract[RunAutotestsCommand, AutotestRunView],
        get_assistant_version: OrchestratorContract[
            AssistantVersionQuery,
            AssistantVersionDetails,
        ],
    ) -> None:
        self._assemble_assistant_version: OrchestratorContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ] = assemble_assistant_version
        self._run_autotests: OrchestratorContract[
            RunAutotestsCommand,
            AutotestRunView,
        ] = run_autotests
        self._get_assistant_version: OrchestratorContract[
            AssistantVersionQuery,
            AssistantVersionDetails,
        ] = get_assistant_version

    def start(
        self, input_data: AssembleAssistantVersionCommand
    ) -> AssistantVersionDetails:
        version: AssistantVersionDetails = self._assemble_assistant_version.execute(
            input_data
        )
        if not input_data.request.run_autotests:
            return version

        self._run_autotests.execute(
            RunAutotestsCommand(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                version_id=version.id,
                languages=input_data.request.languages,
                kinds=input_data.request.kinds,
            )
        )
        return self._get_assistant_version.execute(
            AssistantVersionQuery(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                version_id=version.id,
            )
        )
