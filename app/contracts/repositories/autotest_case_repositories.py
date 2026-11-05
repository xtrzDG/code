"""
Persistence contract of the owner's own checks ("My checks").

Implementations return independent copies: mutating a returned document
does not change stored state until it is saved. A business keeps at most
a few dozen checks, so they are read whole by business.
"""

from collections.abc import Callable
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AutotestCaseRepoContract(RepoContract, Protocol):
    def save(self, case: AutotestCaseDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, case_id: AutotestCaseId
    ) -> AutotestCaseDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[AutotestCaseDocument]:
        """The business's checks, the first written first."""
        raise NotImplementedError

    def delete(self, business_id: BusinessId, case_id: AutotestCaseId) -> None:
        raise NotImplementedError

    def modify(
        self,
        business_id: BusinessId,
        case_id: AutotestCaseId,
        change: Callable[[AutotestCaseDocument], AutotestCaseDocument | None],
    ) -> AutotestCaseDocument | None:
        """
        Store what `change` makes of the check as stored now, in one step;
        None (nothing written) for a missing check or when `change` returns
        None.
        """
        raise NotImplementedError
