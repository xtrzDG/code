"""Seams of the operations module: calendar storage and sync, per-business
locks, and staff notification broadcasting."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.client_contract import ClientContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.dto.operations.calendar_connection import (
    CalendarEventDraft,
    CalendarTokenGrant,
)
from app.schemas.dto.operations.message_texts import StaffMessage
from app.schemas.typings.bookings.constrained_strings import CalendarAuthorizationUrl
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarAuthorizationStateHash,
    CalendarDisplayName,
    CalendarEventId,
    CalendarRefreshToken,
    ExternalCalendarId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)


class CalendarConnectionRepoContract(RepoContract, Protocol):
    def save(self, connection: CalendarConnectionDocument) -> None:
        """Store the connection; a business has at most one."""
        raise NotImplementedError

    def get_by_business(
        self,
        business_id: BusinessId,
    ) -> CalendarConnectionDocument | None:
        raise NotImplementedError

    def delete_by_business(self, business_id: BusinessId) -> None:
        raise NotImplementedError


class CalendarAuthorizationStateRepoContract(RepoContract, Protocol):
    def save(self, state: CalendarAuthorizationStateDocument) -> None:
        raise NotImplementedError

    def find_by_state_hash(
        self,
        state_hash: CalendarAuthorizationStateHash,
    ) -> CalendarAuthorizationStateDocument | None:
        """Look up a pending authorization from the OAuth callback (any business)."""
        raise NotImplementedError


class CalendarEventLinkRepoContract(RepoContract, Protocol):
    def save(self, link: CalendarEventLinkDocument) -> None:
        raise NotImplementedError

    def find_by_booking(
        self,
        business_id: BusinessId,
        booking_id: BookingId,
    ) -> CalendarEventLinkDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[CalendarEventLinkDocument]:
        raise NotImplementedError

    def delete_by_booking(self, business_id: BusinessId, booking_id: BookingId) -> None:
        raise NotImplementedError


class BusinessLockRegistryContract(RegistryContract, Protocol):
    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        """
        Lock serializing booking changes of one business inside this process,
        so a check-then-insert cannot double-book the last unit.
        """
        raise NotImplementedError


class ManagerBroadcastFacilitatorContract(FacilitatorContract, Protocol):
    def broadcast(self, messages: list[StaffMessage]) -> DeliveredNotificationCount:
        """
        Deliver every message to its staff contact and count the deliveries.
        Never raises: one failing contact does not stop the others.
        """
        raise NotImplementedError


class BookingCalendarSyncFacilitatorContract(FacilitatorContract, Protocol):
    def sync(self, booking: BookingDocument) -> None:
        """
        Mirror a booking in the business calendar when one is connected:
        create, update, or delete the event to match the booking status.
        Never raises: calendar failures never break bookings.
        """
        raise NotImplementedError


class GoogleCalendarClientContract(ClientContract, Protocol):
    """Google OAuth 2.0 and Calendar API v3 calls; raises ExternalServiceError."""

    def is_configured(self) -> bool:
        """Whether the OAuth client id, secret and redirect URI are set."""
        raise NotImplementedError

    def build_authorization_url(
        self,
        state: CalendarAuthorizationState,
    ) -> CalendarAuthorizationUrl:
        """Consent page asking for offline access to calendar events."""
        raise NotImplementedError

    def exchange_code(self, code: CalendarAuthorizationCode) -> CalendarTokenGrant:
        raise NotImplementedError

    def refresh_access_token(
        self,
        refresh_token: CalendarRefreshToken,
    ) -> CalendarTokenGrant:
        raise NotImplementedError

    def revoke_token(self, refresh_token: CalendarRefreshToken) -> None:
        raise NotImplementedError

    def get_calendar_name(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
    ) -> CalendarDisplayName | None:
        """The calendar's title (for a primary calendar, the account e-mail)."""
        raise NotImplementedError

    def insert_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event: CalendarEventDraft,
    ) -> CalendarEventId:
        raise NotImplementedError

    def patch_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event_id: CalendarEventId,
        event: CalendarEventDraft,
    ) -> None:
        raise NotImplementedError

    def delete_event(
        self,
        access_token: CalendarAccessToken,
        calendar_id: ExternalCalendarId,
        event_id: CalendarEventId,
    ) -> None:
        """Deleting an event that is already gone is not an error."""
        raise NotImplementedError
