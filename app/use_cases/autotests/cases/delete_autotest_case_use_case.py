from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.autotest_cases import AutotestCaseCommand
from app.schemas.exceptions.application_errors import NotFoundError


class DeleteAutotestCaseUseCase(UseCaseContract[AutotestCaseCommand, None]):
    """
    Delete one of the owner's checks (owner only); the next autotest run no
    longer plays it, while the runs that did keep its results.

    Raises:
        NotFoundError: the check is not this business's.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        autotest_case_repo: AutotestCaseRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo

    def run(self, input_data: AutotestCaseCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        if self._autotest_case_repo.get(business.id, input_data.case_id) is None:
            raise NotFoundError(f"Check {input_data.case_id} was not found.")

        self._autotest_case_repo.delete(business.id, input_data.case_id)
