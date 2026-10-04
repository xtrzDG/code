"""The platform's incident log (a platform collection)."""

from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.dto.paging import KeysetSlice


class IncidentRepoContract(RepoContract, Protocol):
    def save(self, incident: IncidentDocument) -> None:
        raise NotImplementedError

    def list_page(self, page: KeysetSlice) -> list[IncidentDocument]:
        """One keyset page of the log, the newest first (`page_by` on created_at)."""
        raise NotImplementedError
