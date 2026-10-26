from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.dto.niche_texts.niche_text_commands import NicheTextCommand
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest


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
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_NICHE_TEMPLATES,
            )
        )
        self._niche_text_repo.delete_draft(input_data.niche_key)
