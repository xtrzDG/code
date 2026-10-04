from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseList,
    ListAutotestCasesQuery,
)
from app.use_cases.autotests.cases.autotest_case_rules import AUTOTEST_CASE_LIMIT
from app.use_cases.autotests.cases.autotest_case_views import (
    latest_case_results,
    to_case_view,
)


class ListAutotestCasesUseCase(
    UseCaseContract[ListAutotestCasesQuery, AutotestCaseList]
):
    """
    "My checks" (owner only): the business's own checks, the first written
    first, each with how it did in the latest finished autotest run that
    played it (none yet for a check written after that run).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        autotest_case_repo: AutotestCaseRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo

    def run(self, input_data: ListAutotestCasesQuery) -> AutotestCaseList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        results = latest_case_results(
            self._assistant_version_repo, self._autotest_run_repo, business.id
        )
        return AutotestCaseList(
            items=[
                to_case_view(case, results.get(case.id))
                for case in self._autotest_case_repo.list_by_business(business.id)
            ],
            limit=AUTOTEST_CASE_LIMIT,
        )
