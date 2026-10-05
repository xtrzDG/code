"""Deterministic helpers of the guests' booking manage links."""

from typing import Protocol

from app.contracts.utility_contract import UtilityContract
from app.schemas.dto.booking_manage import BookingManageClaims
from app.schemas.typings.bookings.constrained_strings import BookingManageToken


class BookingManageTokenSignerContract(UtilityContract, Protocol):
    def sign(self, claims: BookingManageClaims) -> BookingManageToken:
        """A compact token that carries the claims and their signature."""
        raise NotImplementedError

    def read(self, token: BookingManageToken) -> BookingManageClaims | None:
        """
        The claims of a token this platform signed; None for a forged,
        altered or malformed one. Expiry and the booking's version are the
        caller's checks.
        """
        raise NotImplementedError
