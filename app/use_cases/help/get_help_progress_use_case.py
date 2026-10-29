from app.contracts.help import HelpProgressRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.help_progress import HelpProgressQuery, HelpProgressView
from app.use_cases.help.help_progress_views import progress_view


class GetHelpProgressUseCase(UseCaseContract[HelpProgressQuery, HelpProgressView]):
    """
    GET /v1/me/help: the coach marks the signed-in person closed and the
    newest "What's new" entry they read (nothing yet for a new person).
    """

    def __init__(self, help_progress_repo: HelpProgressRepoContract) -> None:
        self._help_progress_repo: HelpProgressRepoContract = help_progress_repo

    def run(self, input_data: HelpProgressQuery) -> HelpProgressView:
        return progress_view(self._help_progress_repo.find(input_data.user_id))
