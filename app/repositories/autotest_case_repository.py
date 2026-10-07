from collections.abc import Callable

from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AutotestCaseRepository(
    BusinessScopedRepository[AutotestCaseDocument],
    AutotestCaseRepoContract,
):
    """The owner's checks of each business (migration 1112)."""

    def save(self, case: AutotestCaseDocument) -> None:
        self._store(str(case.id), case)

    def get(
        self, business_id: BusinessId, case_id: AutotestCaseId
    ) -> AutotestCaseDocument | None:
        return self._load(business_id, str(case_id))

    def list_by_business(self, business_id: BusinessId) -> list[AutotestCaseDocument]:
        return sorted(
            self._list_in_business(business_id),
            key=lambda case: (int(case.created_at), str(case.id)),
        )

    def delete(self, business_id: BusinessId, case_id: AutotestCaseId) -> None:
        self._remove(business_id, str(case_id))

    def modify(
        self,
        business_id: BusinessId,
        case_id: AutotestCaseId,
        change: Callable[[AutotestCaseDocument], AutotestCaseDocument | None],
    ) -> AutotestCaseDocument | None:
        return self._modify_in_business(business_id, str(case_id), change)
