from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AssistantVersionRepository(
    BusinessScopedRepository[AssistantVersionDocument],
    AssistantVersionRepoContract,
):
    def save(self, version: AssistantVersionDocument) -> None:
        self._store(str(version.id), version)

    def get(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
    ) -> AssistantVersionDocument | None:
        return self._load(business_id, str(version_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AssistantVersionDocument]:
        return sorted(
            self._list_in_business(business_id),
            key=lambda version: version.version_number,
        )


class AutotestRunRepository(
    BusinessScopedRepository[AutotestRunDocument],
    AutotestRunRepoContract,
):
    def save(self, run: AutotestRunDocument) -> None:
        self._store(str(run.id), run)

    def get(
        self,
        business_id: BusinessId,
        run_id: AutotestRunId,
    ) -> AutotestRunDocument | None:
        return self._load(business_id, str(run_id))
