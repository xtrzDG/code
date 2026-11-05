from app.containers.niche_texts.niche_text_dependencies import NicheTextDependencies
from app.containers.niche_texts.niche_text_use_case_factories import (
    NicheTextUseCaseFactories,
)
from app.containers.role_chain_factories import business_scoped_operator
from app.contracts.operator_contract import OperatorContract
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


class NicheTextOperatorFactories:
    """
    One operator per endpoint of the niche template editor, each the
    generic role chain over one use case. Their inputs name no business, so
    they run in the caller's scope: unscoped, on the platform collections
    the drafts and versions live in.
    """

    def __init__(
        self,
        dependencies: NicheTextDependencies,
        use_cases: NicheTextUseCaseFactories,
    ) -> None:
        self._scope = dependencies.storage_scope
        self._use_cases: NicheTextUseCaseFactories = use_cases

    def list_niche_texts(
        self,
    ) -> OperatorContract[NicheTextOverviewQuery, NicheTextStatusList]:
        return business_scoped_operator(self._use_cases.list_niche_texts(), self._scope)

    def get_niche_text_editor(
        self,
    ) -> OperatorContract[NicheTextEditorQuery, NicheTextEditorView]:
        return business_scoped_operator(
            self._use_cases.get_niche_text_editor(), self._scope
        )

    def save_niche_text_draft(
        self,
    ) -> OperatorContract[SaveNicheTextDraftCommand, NicheTextEditorView]:
        return business_scoped_operator(
            self._use_cases.save_niche_text_draft(), self._scope
        )

    def discard_niche_text_draft(self) -> OperatorContract[NicheTextCommand, None]:
        return business_scoped_operator(
            self._use_cases.discard_niche_text_draft(), self._scope
        )

    def publish_niche_texts(
        self,
    ) -> OperatorContract[NicheTextCommand, NicheTextReleaseView]:
        return business_scoped_operator(
            self._use_cases.publish_niche_texts(), self._scope
        )

    def revert_niche_texts(
        self,
    ) -> OperatorContract[RevertNicheTextsCommand, NicheTextReleaseView]:
        return business_scoped_operator(
            self._use_cases.revert_niche_texts(), self._scope
        )

    def list_niche_text_versions(
        self,
    ) -> OperatorContract[NicheTextHistoryQuery, NicheTextHistoryView]:
        return business_scoped_operator(
            self._use_cases.list_niche_text_versions(), self._scope
        )
