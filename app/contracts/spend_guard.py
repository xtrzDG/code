"""The spend guard's side effects: telling owners and the team once."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.spend_guard import SpendLimitPassing


class SpendLimitNoticeFacilitatorContract(FacilitatorContract, Protocol):
    def announce(
        self, passing: SpendLimitPassing, owners: list[ManagerContact]
    ) -> None:
        """
        Tell each owner (in their language, through the staff outbox) and the
        platform team (the platform alert recipients, as queued jobs) that
        the business passed a spend limit today. Never raises.
        """
        raise NotImplementedError
