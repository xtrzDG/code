from typed_time_provider import Microseconds, WallClock

from app.contracts.help import HelpProgressRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.dto.help_progress import ChangelogReadCommand, HelpProgressView
from app.use_cases.help.help_progress_views import empty_progress, progress_view


class ReadChangelogUseCase(UseCaseContract[ChangelogReadCommand, HelpProgressView]):
    """
    PUT /v1/me/help/changelog: the person opened "What's new" and saw up
    to this entry, so its unread dot goes out on every device. The key
    only moves forward: an older tab reporting an older entry changes
    nothing.
    """

    def __init__(
        self,
        help_progress_repo: HelpProgressRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._help_progress_repo: HelpProgressRepoContract = help_progress_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ChangelogReadCommand) -> HelpProgressView:
        now: Microseconds = self._wall_clock.now_unix()
        read_key = input_data.body.read_key

        def move_forward(progress: HelpProgressDocument) -> HelpProgressDocument | None:
            current = progress.changelog_read_key
            if current is not None and str(current) >= str(read_key):
                return None
            return progress.model_copy(
                update={"changelog_read_key": read_key, "updated_at": now}
            )

        return progress_view(
            self._help_progress_repo.change(
                input_data.user_id,
                move_forward,
                empty_progress(input_data.user_id, now),
            )
        )
