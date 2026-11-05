from app.containers.niche_texts.niche_text_dependencies import NicheTextDependencies
from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.niche_texts.niche_text_commands import (
    NicheTextCommand,
    NicheTextEditorQuery,
    NicheTextHistoryQuery,
    NicheTextOverviewQuery,
    RevertNicheTextsCommand,
    SaveNicheTextDraftCommand,
)
from app.schemas.dto.niche_texts.niche_text_views import (
    NicheTextEditorView,
    NicheTextHistoryView,
    NicheTextReleaseView,
    NicheTextStatusList,
)
from app.use_cases.admin.authorize_platform_admin_use_case import (
    AuthorizePlatformAdminUseCase,
)
from app.use_cases.admin.niche_texts.discard_niche_text_draft_use_case import (
    DiscardNicheTextDraftUseCase,
)
from app.use_cases.admin.niche_texts.get_niche_text_editor_use_case import (
    GetNicheTextEditorUseCase,
)
from app.use_cases.admin.niche_texts.list_niche_text_versions_use_case import (
    ListNicheTextVersionsUseCase,
)
from app.use_cases.admin.niche_texts.list_niche_texts_use_case import (
    ListNicheTextsUseCase,
)
from app.use_cases.admin.niche_texts.niche_text_editing import NicheTextSources
from app.use_cases.admin.niche_texts.publish_niche_texts_use_case import (
    PublishNicheTextsUseCase,
)
from app.use_cases.admin.niche_texts.revert_niche_texts_use_case import (
    RevertNicheTextsUseCase,
)
from app.use_cases.admin.niche_texts.save_niche_text_draft_use_case import (
    SaveNicheTextDraftUseCase,
)


class NicheTextUseCaseFactories:
    """
    One typed factory per use case of the niche template editor: the
    overview, a niche's editor in a language, its draft (save, discard),
    publishing, a revert or reset, and the history. Each call builds a new
    use case from the context's dependencies.
    """

    def __init__(self, dependencies: NicheTextDependencies) -> None:
        self._dependencies: NicheTextDependencies = dependencies

    def _admin_check(self) -> PlatformAdminCheck:
        given = self._dependencies
        return AuthorizePlatformAdminUseCase(
            user_repo=given.user_repo,
            session_assurance=given.session_assurance,
            platform_admins=given.platform_admins,
        )

    def _sources(self) -> NicheTextSources:
        given = self._dependencies
        return NicheTextSources(
            niche_templates=given.niche_templates,
            starter_answers=given.starter_answers,
            niche_text_repo=given.niche_text_repo,
        )

    def list_niche_texts(
        self,
    ) -> UseCaseContract[NicheTextOverviewQuery, NicheTextStatusList]:
        given = self._dependencies
        return ListNicheTextsUseCase(
            authorize_platform_admin=self._admin_check(),
            sources=self._sources(),
            user_repo=given.user_repo,
            localized_text_resolver=given.localized_text_resolver,
        )

    def get_niche_text_editor(
        self,
    ) -> UseCaseContract[NicheTextEditorQuery, NicheTextEditorView]:
        given = self._dependencies
        return GetNicheTextEditorUseCase(
            authorize_platform_admin=self._admin_check(),
            sources=self._sources(),
            user_repo=given.user_repo,
            localized_text_resolver=given.localized_text_resolver,
        )

    def save_niche_text_draft(
        self,
    ) -> UseCaseContract[SaveNicheTextDraftCommand, NicheTextEditorView]:
        given = self._dependencies
        return SaveNicheTextDraftUseCase(
            authorize_platform_admin=self._admin_check(),
            sources=self._sources(),
            user_repo=given.user_repo,
            localized_text_resolver=given.localized_text_resolver,
            wall_clock=given.wall_clock,
        )

    def discard_niche_text_draft(self) -> UseCaseContract[NicheTextCommand, None]:
        return DiscardNicheTextDraftUseCase(
            authorize_platform_admin=self._admin_check(),
            niche_text_repo=self._dependencies.niche_text_repo,
        )

    def publish_niche_texts(
        self,
    ) -> UseCaseContract[NicheTextCommand, NicheTextReleaseView]:
        given = self._dependencies
        return PublishNicheTextsUseCase(
            authorize_platform_admin=self._admin_check(),
            sources=self._sources(),
            audit_log_repo=given.audit_log_repo,
            step_up=given.step_up,
            wall_clock=given.wall_clock,
        )

    def revert_niche_texts(
        self,
    ) -> UseCaseContract[RevertNicheTextsCommand, NicheTextReleaseView]:
        given = self._dependencies
        return RevertNicheTextsUseCase(
            authorize_platform_admin=self._admin_check(),
            sources=self._sources(),
            audit_log_repo=given.audit_log_repo,
            step_up=given.step_up,
            wall_clock=given.wall_clock,
        )

    def list_niche_text_versions(
        self,
    ) -> UseCaseContract[NicheTextHistoryQuery, NicheTextHistoryView]:
        given = self._dependencies
        return ListNicheTextVersionsUseCase(
            authorize_platform_admin=self._admin_check(),
            niche_text_repo=given.niche_text_repo,
            user_repo=given.user_repo,
        )
