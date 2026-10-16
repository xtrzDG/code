"""Deterministic helpers of staff notifications."""

from typing import Protocol

from app.contracts.utility_contract import UtilityContract
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.notifications.constrained_strings import StaffLinkToken


class StaffLinkSignerContract(UtilityContract, Protocol):
    def sign(self, claims: StaffLinkClaims) -> StaffLinkToken:
        """A compact token that carries the claims and their signature."""
        raise NotImplementedError

    def read(self, token: StaffLinkToken) -> StaffLinkClaims | None:
        """
        The claims of a token this platform signed; None for a forged,
        altered or malformed one. Expiry is the caller's check.
        """
        raise NotImplementedError
