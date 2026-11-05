from typed_time_provider import Microseconds, WallClock

from app.contracts.help import HelpProgressRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.dto.help_progress import CoachMarkSeenCommand, HelpProgressView
from app.use_cases.help.help_progress_views import (
    MAX_SEEN_COACH_MARKS,
    empty_progress,
    progress_view,
)


class MarkCoachMarkSeenUseCase(UseCaseContract[CoachMarkSeenCommand, HelpProgressView]):
    """
    PUT /v1/me/help/coach-marks/{key}: the person closed a one-time hint,
    so it never shows again on any of their devices. Idempotent; at most
    MAX_SEEN_COACH_MARKS are kept (the oldest go first).
    """

    def __init__(
        self,
        help_progress_repo: HelpProgressRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._help_progress_repo: HelpProgressRepoContract = help_progress_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CoachMarkSeenCommand) -> HelpProgressView:
        now: Microseconds = self._wall_clock.now_unix()

        def add_mark(progress: HelpProgressDocument) -> HelpProgressDocument | None:
            if input_data.key in progress.seen_coach_marks:
                return None
            seen = [*progress.seen_coach_marks, input_data.key]
            return progress.model_copy(
                update={
                    "seen_coach_marks": seen[-MAX_SEEN_COACH_MARKS:],
                    "updated_at": now,
                }
            )

        return progress_view(
            self._help_progress_repo.change(
                input_data.user_id, add_mark, empty_progress(input_data.user_id, now)
            )
        )
