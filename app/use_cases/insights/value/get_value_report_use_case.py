from app.contracts.repositories.value_repositories import ValueReportRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_reports import ValueReportQuery, ValueReportView
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.insights.value.value_snapshots import build_value_report_view


class GetValueReportUseCase(UseCaseContract[ValueReportQuery, ValueReportView]):
    """One stored report of the business, as it was sent (owners)."""

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        value_report_repo: ValueReportRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._value_report_repo: ValueReportRepoContract = value_report_repo

    def run(self, input_data: ValueReportQuery) -> ValueReportView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        report: ValueReportDocument | None = self._value_report_repo.get(
            business.id, input_data.report_id
        )
        if report is None:
            raise NotFoundError("This report was not found.")

        return build_value_report_view(report)
