from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextReleaseDocument,
)
from app.schemas.dto.niche_texts.niche_text_commands import NicheTextOverviewQuery
from app.schemas.dto.niche_texts.niche_text_views import NicheTextStatusList
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.admin.niche_texts.niche_text_editing import (
    NicheTextSources,
    display_names,
)
from app.use_cases.admin.niche_texts.niche_text_views import status_view
from app.utilities.knowledge.localized_texts import FALLBACK_LANGUAGE_TAG


class ListNicheTextsUseCase(
    UseCaseContract[NicheTextOverviewQuery, NicheTextStatusList]
):
    """
    GET /v1/admin/niche-templates: every niche with the version of its
    texts in force (0: the code template), how many texts it rewords, who
    published it and whether a draft waits. Three reads whatever the
    number of niches (the newest versions, the drafts, the names).
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

    def run(self, input_data: NicheTextOverviewQuery) -> NicheTextStatusList:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_NICHE_TEMPLATES,
            )
        )
        language: LanguageTag = input_data.language or FALLBACK_LANGUAGE_TAG
        templates: list[NicheTemplate] = self._sources.niche_templates.list_all()
        niche_keys: list[NicheKey] = [template.key for template in templates]
        repo = self._sources.niche_text_repo
        releases: dict[NicheKey, NicheTextReleaseDocument] = {
            release.niche_key: release for release in repo.latest_releases(niche_keys)
        }
        drafts: dict[NicheKey, NicheTextDraftDocument] = {
            draft.niche_key: draft for draft in repo.list_drafts(niche_keys)
        }
        names = display_names(
            self._user_repo, (release.published_by for release in releases.values())
        )
        return NicheTextStatusList(
            language=language,
            items=[
                status_view(
                    template,
                    language,
                    releases.get(template.key),
                    drafts.get(template.key),
                    names.get(releases[template.key].published_by)
                    if template.key in releases
                    else None,
                    self._resolver,
                )
                for template in templates
            ],
        )
