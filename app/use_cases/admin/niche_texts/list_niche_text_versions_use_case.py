from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.niche_texts import NicheTextReleaseDocument
from app.schemas.dto.niche_texts.niche_text_commands import NicheTextHistoryQuery
from app.schemas.dto.niche_texts.niche_text_views import NicheTextHistoryView
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.admin.niche_texts.niche_text_editing import display_names
from app.use_cases.admin.niche_texts.niche_text_views import release_view

# The history the editor shows; older versions stay stored (a revert to one
# names its number).
HISTORY_LIMIT: DocumentQueryLimit = DocumentQueryLimit(100)


class ListNicheTextVersionsUseCase(
    UseCaseContract[NicheTextHistoryQuery, NicheTextHistoryView]
):
    """
    GET /v1/admin/niche-templates/{niche_key}/versions: the niche's
    published versions, newest first, with who published each and how
    (published, reverted to version N, reset to the code template).
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        niche_text_repo: NicheTextRepoContract,
        user_repo: UserRepoContract,
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._niche_text_repo: NicheTextRepoContract = niche_text_repo
        self._user_repo: UserRepoContract = user_repo

    def run(self, input_data: NicheTextHistoryQuery) -> NicheTextHistoryView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_NICHE_TEMPLATES,
            )
        )
        releases: list[NicheTextReleaseDocument] = self._niche_text_repo.list_releases(
            input_data.niche_key, HISTORY_LIMIT
        )
        names = display_names(
            self._user_repo, (release.published_by for release in releases)
        )
        return NicheTextHistoryView(
            niche_key=input_data.niche_key,
            items=[
                release_view(release, names.get(release.published_by))
                for release in releases
            ],
        )
