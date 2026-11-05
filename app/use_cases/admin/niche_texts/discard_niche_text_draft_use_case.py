from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.niche_texts.niche_text_commands import NicheTextCommand
from app.use_cases.admin.niche_texts.niche_text_editing import authorize_editor


class DiscardNicheTextDraftUseCase(UseCaseContract[NicheTextCommand, None]):
    """
    DELETE /v1/admin/niche-templates/{niche_key}/draft: forget the niche's
    draft; the version in force stays. Nothing to discard is not an error.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        niche_text_repo: NicheTextRepoContract,
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._niche_text_repo: NicheTextRepoContract = niche_text_repo

    def run(self, input_data: NicheTextCommand) -> None:
        authorize_editor(self._authorize_platform_admin, input_data.user_id)
        self._niche_text_repo.delete_draft(input_data.niche_key)
