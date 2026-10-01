from app.contracts.repositories import DpaAcceptanceRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import DpaAcceptanceDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.compliance import DpaAcceptanceView, DpaStatusView
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion


class GetDpaStatusUseCase(UseCaseContract[BusinessQuery, DpaStatusView]):
    """
    Tell owners and staff whether the agreement version in force is accepted.

    A newer agreement version (a settings change) makes earlier acceptances
    stale until an owner accepts again.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        dpa_acceptance_repo: DpaAcceptanceRepoContract,
        app_settings: AppSettings,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._dpa_acceptance_repo: DpaAcceptanceRepoContract = dpa_acceptance_repo
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: BusinessQuery) -> DpaStatusView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        current_version: DpaDocumentVersion = self._app_settings.dpa_document_version
        acceptances: list[DpaAcceptanceDocument] = (
            self._dpa_acceptance_repo.list_by_business(business.id)
        )
        latest_acceptance: DpaAcceptanceDocument | None = (
            acceptances[-1] if acceptances else None
        )
        return DpaStatusView(
            business_id=business.id,
            current_document_version=current_version,
            is_current_version_accepted=any(
                acceptance.document_version == current_version
                for acceptance in acceptances
            ),
            latest_acceptance=None
            if latest_acceptance is None
            else DpaAcceptanceView(
                id=latest_acceptance.id,
                document_version=latest_acceptance.document_version,
                accepted_by=latest_acceptance.accepted_by,
                accepted_at=latest_acceptance.accepted_at,
            ),
        )
