"""
Contracts of the revenue features: the bookings' side of the waitlist
(places held for waiting customers, places freed by cancellations and
moves) and of the campaigns (which bookings they brought), and the
niches' default rebooking rules.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.bookings import BookingOrigin
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.dto.growth.rebooking_rules import RebookingRule
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.waitlist.booleans import (
    IsStaffBookingChange,
    IsWaitlistEnabled,
)


class GrowthBookingsFacilitatorContract(FacilitatorContract, Protocol):
    """
    What the booking use cases ask of the waitlist and the campaigns. Each
    call is made inside the business's booking lock where it says so, so a
    held place and a booking can never both take one unit.
    """

    def held_places(
        self,
        business_id: BusinessId,
        ends_after: BookingSearchBoundSeconds,
        now: Microseconds,
        holder: ContactId | None,
    ) -> list[BookingDocument]:
        """
        The places held for waiting customers (offers whose hold has not
        run out) that end after `ends_after`, as unsaved bookings a
        placement respects; a place held for `holder` is left out, so the
        customer it is held for can take it. Under the booking lock.
        """
        raise NotImplementedError

    def is_waitlist_open(self, business_id: BusinessId) -> IsWaitlistEnabled:
        """Whether the business keeps a waitlist (on unless the owner turned it off)."""
        raise NotImplementedError

    def attribute(
        self, booking: BookingDocument, now: Microseconds
    ) -> BookingOrigin | None:
        """
        Where a new booking came from: WAITLIST when it takes the place
        held for its customer (the entry becomes BOOKED), CAMPAIGN when its
        customer was invited back within the last week (the message becomes
        BOOKED), else None. Under the booking lock, before the booking is
        saved; never for test bookings.
        """
        raise NotImplementedError

    def notice_freed(
        self,
        booking: BookingDocument,
        place: FreedPlace,
        now: Microseconds,
        is_staff_change: IsStaffBookingChange = False,
    ) -> None:
        """
        A cancellation or a move gave up `place`: queue the job that offers
        it to the first waiting customer who fits (a staff change in the
        cabinet a little later, so a quick Undo still finds the place).
        Never raises: a booking change never fails for the waitlist.
        """
        raise NotImplementedError


class RebookingRuleRegistryContract(RegistryContract, Protocol):
    def get(self, niche_key: NicheKey) -> RebookingRule:
        """The niche's default rule (every niche has one)."""
        raise NotImplementedError
