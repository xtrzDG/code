from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.security_nudges import (
    SecurityNudgeQuery,
    SecurityNudgeSource,
    SecurityNudgeView,
)


class GetSecurityNudgeUseCase(UseCaseContract[SecurityNudgeQuery, SecurityNudgeView]):
    """
    The banner "Protect your customers' data: turn on a second factor" over
    the cabinet. Owners and staff may ask; it is shown to owners only.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        describe_security_nudge: UseCaseContract[
            SecurityNudgeSource, SecurityNudgeView
        ],
    ) -> None:
        self._authorize: UseCaseContract[BusinessAccessRequest, BusinessDocument] = (
            authorize_business_access
        )
        self._describe: UseCaseContract[SecurityNudgeSource, SecurityNudgeView] = (
            describe_security_nudge
        )

    def run(self, input_data: SecurityNudgeQuery) -> SecurityNudgeView:
        business: BusinessDocument = self._authorize.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        return self._describe.run(
            SecurityNudgeSource(business=business, user_id=input_data.user_id)
        )
