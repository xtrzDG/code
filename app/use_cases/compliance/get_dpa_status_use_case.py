from app.contracts.legal_registries import LegalDocumentRegistryContract
from app.contracts.repositories.compliance_repositories import DpaAcceptanceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.compliance import DpaStatusView
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.compliance.dpa_status_views import dpa_status_view
from app.utilities.localization.cldr_language_names import ENGLISH_LOCALE_IDENTIFIER


class GetDpaStatusUseCase(UseCaseContract[BusinessQuery, DpaStatusView]):
    """
    Tell owners and staff whether the agreement version in force is accepted.

    A newer agreement version (a settings change) makes earlier acceptances
    stale until an owner accepts again (within 30 days of its date; the
    cabinet shows owners a banner). The status links the text of the
    version in force when the repository has it.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        dpa_acceptance_repo: DpaAcceptanceRepoContract,
        legal_document_registry: LegalDocumentRegistryContract,
        app_settings: AppSettings,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._dpa_acceptance_repo: DpaAcceptanceRepoContract = dpa_acceptance_repo
        self._legal_document_registry: LegalDocumentRegistryContract = (
            legal_document_registry
        )
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: BusinessQuery) -> DpaStatusView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        current_version: DpaDocumentVersion = self._app_settings.dpa_document_version
        return dpa_status_view(
            business,
            current_version,
            self._dpa_acceptance_repo.list_by_business(business.id),
            has_text=self._legal_document_registry.find_dpa(
                current_version, LanguageTag(ENGLISH_LOCALE_IDENTIFIER)
            )
            is not None,
        )
