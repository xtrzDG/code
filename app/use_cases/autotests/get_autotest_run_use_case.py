from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestRunStatus
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.assistant_commands import AssistantVersionQuery
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import AutotestRunViewSource
from app.schemas.exceptions.application_errors import NotFoundError


class GetAutotestRunUseCase(UseCaseContract[AssistantVersionQuery, AutotestRunView]):
    """
    The latest autotest run of a version (owners and staff), compared with
    the finished run of the version that was live when it started.
    """

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

        if run.status is AutotestRunStatus.FINISHED:
            # The worker saves the version's final status before it marks
            # the run finished; read the version again so a run that
            # finished between the two reads never shows it still testing.
            version = (
                self._assistant_version_repo.get(business.id, version.id) or version
            )

        baseline_run: AutotestRunDocument | None = self._read_baseline_run(
            business, run
        )
        return self._autotest_run_view_transformer.transform(
            AutotestRunViewSource(
                run=run,
                version=version,
                baseline_run=baseline_run,
                baseline_version=(
                    self._assistant_version_repo.get(
                        business.id, baseline_run.assistant_version_id
                    )
                    if baseline_run is not None
                    else None
                ),
            )
        )

    def _read_baseline_run(
        self, business: BusinessDocument, run: AutotestRunDocument
    ) -> AutotestRunDocument | None:
        if (
            run.status is not AutotestRunStatus.FINISHED
            or run.compared_to_run_id is None
        ):
            return None

        baseline_run: AutotestRunDocument | None = self._autotest_run_repo.get(
            business.id, run.compared_to_run_id
        )
        if (
            baseline_run is None
            or baseline_run.status is not AutotestRunStatus.FINISHED
        ):
            return None

        return baseline_run
