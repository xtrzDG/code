from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.setup import ApplyAttentionCode
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
    AssembleAssistantVersionRequest,
    RunAutotestsCommand,
)
from app.schemas.dto.assistants.assistant_views import (
    AssistantVersionDetails,
    AutotestRunView,
)
from app.schemas.dto.assistants.autotest_runs import AutotestRunPlan
from app.schemas.dto.setup.apply_changes import (
    AppliedVersion,
    ApplyBuildFailure,
    ApplyChangesCommand,
    ApplyChangesQuery,
    ApplyChangesView,
    ApplyStart,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.setup.booleans import IsApplyInProgress


class ApplyChangesOrchestrator(
    OrchestratorContract[ApplyChangesCommand, ApplyChangesView]
):
    """
    "Apply changes" in one call: register the apply (idempotent), build a
    version from the current profile and knowledge, stop at once on a
    missing launch condition, and hand the automatic checks to the
    background worker, which publishes the version when they pass. A
    version already checked and still up to date is published right away.
    Whatever happens comes back as the apply's progress in plain words
    (202): a profile the assistant cannot be built from, or checks that
    cannot start, end the apply as NEEDS_ATTENTION instead of an error.
    """

    def __init__(
        self,
        start_apply_changes: UseCaseContract[ApplyChangesCommand, ApplyStart],
        assemble_assistant_version: UseCaseContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ],
        check_applied_version: UseCaseContract[AppliedVersion, IsApplyInProgress],
        start_autotest_run: UseCaseContract[RunAutotestsCommand, AutotestRunPlan],
        enqueue_autotest_run: UseCaseContract[AutotestRunPlan, AutotestRunView],
        publish_applied_version: UseCaseContract[AppliedVersion, None],
        fail_apply_changes: UseCaseContract[ApplyBuildFailure, None],
        get_apply_changes: UseCaseContract[ApplyChangesQuery, ApplyChangesView],
    ) -> None:
        self._start_apply_changes: UseCaseContract[ApplyChangesCommand, ApplyStart] = (
            start_apply_changes
        )
        self._assemble_assistant_version: UseCaseContract[
            AssembleAssistantVersionCommand,
            AssistantVersionDetails,
        ] = assemble_assistant_version
        self._check_applied_version: UseCaseContract[
            AppliedVersion, IsApplyInProgress
        ] = check_applied_version
        self._start_autotest_run: UseCaseContract[
            RunAutotestsCommand, AutotestRunPlan
        ] = start_autotest_run
        self._enqueue_autotest_run: UseCaseContract[
            AutotestRunPlan, AutotestRunView
        ] = enqueue_autotest_run
        self._publish_applied_version: UseCaseContract[AppliedVersion, None] = (
            publish_applied_version
        )
        self._fail_apply_changes: UseCaseContract[ApplyBuildFailure, None] = (
            fail_apply_changes
        )
        self._get_apply_changes: UseCaseContract[
            ApplyChangesQuery, ApplyChangesView
        ] = get_apply_changes

    def execute(self, input_data: ApplyChangesCommand) -> ApplyChangesView:
        start: ApplyStart = self._start_apply_changes.run(input_data)
        if start.is_new and start.version_to_publish is not None:
            self._publish_applied_version.run(
                AppliedVersion(
                    business_id=input_data.business_id,
                    assistant_version_id=start.version_to_publish,
                )
            )
        elif start.is_new:
            self._build_and_check(input_data)

        return self._get_apply_changes.run(
            ApplyChangesQuery(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )

    def _build_and_check(self, command: ApplyChangesCommand) -> None:
        try:
            version: AssistantVersionDetails = self._assemble_assistant_version.run(
                AssembleAssistantVersionCommand(
                    user_id=command.user_id,
                    business_id=command.business_id,
                    request=AssembleAssistantVersionRequest(run_autotests=False),
                )
            )
        except ValidationFailedError:
            self._fail(command, None, ApplyAttentionCode.PROFILE_INCOMPLETE)
            return
        except ApplicationError:
            self._fail(command, None, ApplyAttentionCode.BUILD_FAILED)
            return

        applied = AppliedVersion(
            business_id=command.business_id,
            assistant_version_id=version.id,
        )
        if not self._check_applied_version.run(applied):
            return

        try:
            plan: AutotestRunPlan = self._start_autotest_run.run(
                RunAutotestsCommand(
                    user_id=command.user_id,
                    business_id=command.business_id,
                    version_id=version.id,
                )
            )
            self._enqueue_autotest_run.run(plan)
        except ApplicationError:
            self._fail(command, version.id, ApplyAttentionCode.CHECKS_STOPPED)

    def _fail(
        self,
        command: ApplyChangesCommand,
        version_id: AssistantVersionId | None,
        code: ApplyAttentionCode,
    ) -> None:
        self._fail_apply_changes.run(
            ApplyBuildFailure(
                business_id=command.business_id,
                assistant_version_id=version_id,
                code=code,
            )
        )
