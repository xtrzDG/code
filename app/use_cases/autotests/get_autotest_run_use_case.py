from app.contracts.repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants import (
    AssistantVersionQuery,
    AutotestRunView,
    AutotestRunViewSource,
)
from app.schemas.exceptions.application_errors import NotFoundError


class GetAutotestRunUseCase(UseCaseContract[AssistantVersionQuery, AutotestRunView]):
    """The latest autotest run of a version (owners and staff)."""

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        autotest_run_view_transformer: TransformerContract[
            AutotestRunViewSource,
            AutotestRunView,
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._autotest_run_view_transformer: TransformerContract[
            AutotestRunViewSource,
            AutotestRunView,
        ] = autotest_run_view_transformer

    def run(self, input_data: AssistantVersionQuery) -> AutotestRunView:
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

        run: AutotestRunDocument | None = (
            self._autotest_run_repo.get(business.id, version.autotest_run_id)
            if version.autotest_run_id is not None
            else None
        )
        if run is None:
            raise NotFoundError(
                f"Version {version.version_number} has no autotest run yet."
            )

        return self._autotest_run_view_transformer.transform(
            AutotestRunViewSource(run=run, version=version)
        )
