"""
Persistence contracts of assistant versions and their autotest runs.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved. Every business-owned document is
looked up through its business id, so one tenant never sees another's data.
"""

from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId, AutotestRunId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AssistantVersionRepoContract(RepoContract, Protocol):
    def save(self, version: AssistantVersionDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
    ) -> AssistantVersionDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[AssistantVersionDocument]:
        """Return versions ordered by version_number ascending."""
        raise NotImplementedError


class AutotestRunRepoContract(RepoContract, Protocol):
    def save(self, run: AutotestRunDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        run_id: AutotestRunId,
    ) -> AutotestRunDocument | None:
        raise NotImplementedError
