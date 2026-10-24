"""
Persistence contract of the client standings: the platform admin's client
list as the `refresh_client_standings` job ranks it (a platform collection,
read and written platform-wide by platform admins and the worker only).
"""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.client_health import AdminClientSort
from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.dto.admin import AdminClientTotals
from app.schemas.dto.client_standings import (
    ClientChoices,
    ClientListPositions,
    ClientStandingFilter,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.constrained_integers import ClientCount


class ClientStandingRepoContract(RepoContract, Protocol):
    def get_many(
        self, business_ids: Sequence[BusinessId]
    ) -> dict[BusinessId, ClientStandingDocument]:
        """The standings of these clients that exist, one read."""
        raise NotImplementedError

    def save_many(self, standings: Sequence[ClientStandingDocument]) -> None:
        """Store these standings (each under its business id), one write."""
        raise NotImplementedError

    def move(self, business_id: BusinessId, positions: ClientListPositions) -> None:
        """Set the positions of a stored standing (a missing one is left out)."""
        raise NotImplementedError

    def page(
        self,
        sort: AdminClientSort,
        where: ClientStandingFilter,
        window: KeysetSlice,
    ) -> list[ClientStandingDocument]:
        """One keyset page in the order `sort` (position ascending)."""
        raise NotImplementedError

    def count(self, where: ClientStandingFilter) -> ClientCount:
        """How many standings pass the filter (a database count)."""
        raise NotImplementedError

    def tally(self) -> AdminClientTotals:
        """Every client counted by health and margin (one grouped count)."""
        raise NotImplementedError

    def list_choices(self) -> ClientChoices:
        """The countries and niches of every client (one grouped count)."""
        raise NotImplementedError
