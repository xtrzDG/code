from app.contracts.repositories.value_repositories import ValueReportRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.value.value_reports import ValueReportPage, ValueReportPageQuery
from app.use_cases.insights.value.value_snapshots import build_value_report_view
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListValueReportsUseCase(UseCaseContract[ValueReportPageQuery, ValueReportPage]):
    """
    The stored reports of a kind (monthly by default), newest period
    first, one keyset page at a time (the Reports page; owners). Totals
    only, no personal data, so no audit entry.
    """

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

    def run(self, input_data: ValueReportPageQuery) -> ValueReportPage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        fetched: list[ValueReportDocument] = self._value_report_repo.page_by_business(
            business.id, input_data.kind, read_slice(input_data.page)
        )
        items, next_cursor = finish_page(
            fetched,
            input_data.page,
            sort_key=lambda report: int(report.starts_at),
            item_id=lambda report: str(report.id),
        )
        return ValueReportPage(
            items=[build_value_report_view(report) for report in items],
            next_cursor=next_cursor,
        )
