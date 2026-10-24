from typed_time_provider import Microseconds, WallClock

from app.contracts.help import HelpProgressRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.dto.help_progress import HelpProgressQuery
from app.use_cases.help.help_progress_views import empty_progress


class ResetCoachMarksUseCase(UseCaseContract[HelpProgressQuery, None]):
    """
    DELETE /v1/me/help/coach-marks: "Show the tips again" in the account
    panel; the changelog's read entry stays.
    """

    def __init__(
        self,
        help_progress_repo: HelpProgressRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._help_progress_repo: HelpProgressRepoContract = help_progress_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: HelpProgressQuery) -> None:
        now: Microseconds = self._wall_clock.now_unix()

        def forget_marks(progress: HelpProgressDocument) -> HelpProgressDocument | None:
            if not progress.seen_coach_marks:
                return None
            return progress.model_copy(
                update={"seen_coach_marks": [], "updated_at": now}
            )

        self._help_progress_repo.change(
            input_data.user_id, forget_marks, empty_progress(input_data.user_id, now)
        )
