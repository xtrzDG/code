from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.setup_repositories import AssistantApplyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.setup import ApplyChangesStage
from app.schemas.domain.setup import ApplyAttentionReason
from app.schemas.dto.setup.apply_changes import ApplyBuildFailure
from app.use_cases.assistants.apply.apply_records import move_apply


class FailApplyChangesUseCase(UseCaseContract[ApplyBuildFailure, None]):
    """
    An apply that could not go on (the version could not be built, or its
    checks could not start) needs the owner's attention, with the reason.
    """

    def __init__(
        self,
        assistant_apply_repo: AssistantApplyRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._assistant_apply_repo: AssistantApplyRepoContract = assistant_apply_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ApplyBuildFailure) -> None:
        move_apply(
            self._assistant_apply_repo,
            input_data.business_id,
            input_data.assistant_version_id,
            ApplyChangesStage.NEEDS_ATTENTION,
            self._wall_clock.now_unix(),
            [
                ApplyAttentionReason(
                    code=input_data.code,
                    details=[] if input_data.detail is None else [input_data.detail],
                )
            ],
        )
