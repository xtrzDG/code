from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants import AssistantVersionQuery
from app.schemas.dto.go_live import GoLiveReadiness, GoLiveReadinessRequest
from app.schemas.exceptions.application_errors import NotFoundError


class GetGoLiveReadinessUseCase(
    UseCaseContract[AssistantVersionQuery, GoLiveReadiness]
):
    """
    The go-live checklist of one version for the cabinet (owners and
    staff): the same checks that guard publishing and rollback.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        check_go_live_readiness: UseCaseContract[
            GoLiveReadinessRequest, GoLiveReadiness
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._check_go_live_readiness: UseCaseContract[
            GoLiveReadinessRequest, GoLiveReadiness
        ] = check_go_live_readiness

    def run(self, input_data: AssistantVersionQuery) -> GoLiveReadiness:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id,
            input_data.version_id,
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {input_data.version_id} was not found."
            )

        return self._check_go_live_readiness.run(
            GoLiveReadinessRequest(business=business, version=version)
        )
