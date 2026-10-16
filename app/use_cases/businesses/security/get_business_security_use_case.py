from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.mfa import BusinessSecurityView
from app.use_cases.businesses.security.business_security_views import (
    build_business_security_view,
)


class GetBusinessSecurityUseCase(UseCaseContract[BusinessQuery, BusinessSecurityView]):
    """
    Whether the business asks its team to sign in with two factors, and how
    many members have no authenticator yet (owners and staff may read it).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        totp_factor_repo: TotpFactorRepoContract,
        session_assurance: SessionAssuranceContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._session_assurance: SessionAssuranceContract = session_assurance

    def run(self, input_data: BusinessQuery) -> BusinessSecurityView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return build_business_security_view(
            business,
            self._totp_factor_repo,
            self._session_assurance.current(),
            input_data.user_id,
        )
