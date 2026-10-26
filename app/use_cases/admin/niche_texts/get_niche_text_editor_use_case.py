from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.dto.niche_texts.niche_text_commands import NicheTextEditorQuery
from app.schemas.dto.niche_texts.niche_text_views import NicheTextEditorView
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.use_cases.admin.niche_texts.niche_text_editing import NicheTextSources
from app.use_cases.admin.niche_texts.niche_text_views import load_editor_view
from app.utilities.knowledge.localized_texts import FALLBACK_LANGUAGE_TAG
from app.utilities.niches.niche_text_checks import check_language


class GetNicheTextEditorUseCase(
    UseCaseContract[NicheTextEditorQuery, NicheTextEditorView]
):
    """
    GET /v1/admin/niche-templates/{niche_key}?language=: every text an
    admin may reword in one of the cabinet's languages, the code's wording
    beside the published and the draft one, and the questions' structure
    for the preview of the profile as an owner sees it.

    Raises:
        ValidationFailedError: a language the cabinet does not speak.
    """

    def __init__(
        self,
        authorize_platform_admin: PlatformAdminCheck,
        sources: NicheTextSources,
        user_repo: UserRepoContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._authorize_platform_admin: PlatformAdminCheck = authorize_platform_admin
        self._sources: NicheTextSources = sources
        self._user_repo: UserRepoContract = user_repo
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def run(self, input_data: NicheTextEditorQuery) -> NicheTextEditorView:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_NICHE_TEMPLATES,
            )
        )
        return load_editor_view(
            self._sources,
            self._user_repo,
            self._resolver,
            input_data.niche_key,
            check_language(input_data.language or FALLBACK_LANGUAGE_TAG),
        )
