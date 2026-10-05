from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.legal import (
    LegalOperatorView,
    LegalOverviewQuery,
    LegalOverviewView,
)


class GetLegalOverviewUseCase(UseCaseContract[LegalOverviewQuery, LegalOverviewView]):
    """
    GET /v1/legal/overview (public): whether the legal texts are still
    drafts (until the operator sets LEGAL_TEXTS_FINAL after a lawyer's
    review), the data processing agreement in force (DPA_DOCUMENT_VERSION)
    and the operator's details from the seller settings (SELLER_*), for the
    public /privacy, /terms, /dpa, /security and /contact pages.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: LegalOverviewQuery) -> LegalOverviewView:
        del input_data
        seller = self._app_settings.seller
        return LegalOverviewView(
            is_draft=not self._app_settings.public_site.are_legal_texts_final,
            dpa_version=self._app_settings.dpa_document_version,
            operator=LegalOperatorView(
                legal_name=seller.legal_name,
                address=seller.address,
                email=seller.email,
                tax_id=seller.tax_id,
                country_code=seller.country_code,
            ),
        )
