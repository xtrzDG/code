"""Connecting Google Calendar and mirroring bookings in it."""

import hashlib
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.calendar.google_calendar_sync_facilitator import (
    GoogleCalendarSyncFacilitator,
    summarize_sync_failure,
)
from app.repositories.calendar_repositories import (
    CalendarAuthorizationStateRepository,
    CalendarConnectionRepository,
    CalendarEventLinkRepository,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.calendar import CalendarConnectionFailure
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.dto.calendar import CalendarConnectionOutcome
from app.schemas.dto.operations.calendar_connection import (
    CalendarConnectUrlView,
    CompleteCalendarConnectionCommand,
    DisconnectCalendarCommand,
    StartCalendarConnectionCommand,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarAuthorizationStateHash,
    CalendarProviderErrorCode,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.transformers.notifications.calendar_event_text_transformer import (
    CalendarEventTextTransformer,
)
from app.use_cases.calendar.complete_google_calendar_connection_use_case import (
    CompleteGoogleCalendarConnectionUseCase,
)
from app.use_cases.calendar.disconnect_google_calendar_use_case import (
    DisconnectGoogleCalendarUseCase,
)
from app.use_cases.calendar.start_google_calendar_connection_use_case import (
    StartGoogleCalendarConnectionUseCase,
)
from tests.operations.fake_google import FakeGoogle
from tests.operations.fakes import ReversingSecretCipher
from tests.operations.operations_world import OperationsWorld


class CalendarWorld:
    """A Tbilisi restaurant whose owner connects Google Calendar."""

    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.google = FakeGoogle()
        self.client = self.google.client()
        self.cipher = ReversingSecretCipher()
        self.connection_repo = CalendarConnectionRepository(
            InMemoryDocumentCollectionAdapter[CalendarConnectionDocument](
                CalendarConnectionDocument
            )
        )
        self.state_repo = CalendarAuthorizationStateRepository(
            InMemoryDocumentCollectionAdapter[CalendarAuthorizationStateDocument](
                CalendarAuthorizationStateDocument
            )
        )
        self.link_repo = CalendarEventLinkRepository(
            InMemoryDocumentCollectionAdapter[CalendarEventLinkDocument](
                CalendarEventLinkDocument
            )
        )
        self.owner_id = UserId()
        self.business = self.world.add_business(owner_id=self.owner_id)
        self.world.add_profile(self.business)
        self.table = self.world.add_resource(self.business, "Table 4")
        self.contact = self.world.add_contact(self.business, "Nino", "+995555123456")
        self.sync = GoogleCalendarSyncFacilitator(
            connection_repo=self.connection_repo,
            event_link_repo=self.link_repo,
            business_repo=self.world.business_repo,
            resource_repo=self.world.resource_repo,
            contact_repo=self.world.contact_repo,
            calendar_client=self.client,
            secret_cipher=self.cipher,
            phone_number_parser=self.world.phone_parser,
            event_text_transformer=CalendarEventTextTransformer(self.world.resolver),
            wall_clock=self.world.clock.wall_clock,
        )

    def start_view(
        self, business_id: BusinessId | None = None
    ) -> CalendarConnectUrlView:
        return StartGoogleCalendarConnectionUseCase(
            business_repo=self.world.business_repo,
            authorization_state_repo=self.state_repo,
            calendar_client=self.client,
            wall_clock=self.world.clock.wall_clock,
        ).run(
            StartCalendarConnectionCommand(
                business_id=business_id or self.business.id, user_id=self.owner_id
            )
        )

    def start(self) -> CalendarAuthorizationState:
        query = parse_qs(urlsplit(str(self.start_view().authorization_url)).query)
        return CalendarAuthorizationState(query["state"][0])

    def complete(
        self,
        state: CalendarAuthorizationState | None,
        code: str | None = "good-code",
        provider_error: str | None = None,
        user_id: UserId | None = None,
    ) -> CalendarConnectionOutcome:
        return CompleteGoogleCalendarConnectionUseCase(
            authorization_state_repo=self.state_repo,
            connection_repo=self.connection_repo,
            calendar_client=self.client,
            secret_cipher=self.cipher,
            wall_clock=self.world.clock.wall_clock,
        ).run(
            CompleteCalendarConnectionCommand(
                user_id=self.owner_id if user_id is None else user_id,
                state=state,
                code=None if code is None else CalendarAuthorizationCode(code),
                provider_error=(
                    None
                    if provider_error is None
                    else CalendarProviderErrorCode(provider_error)
                ),
            )
        )

    def disconnect(self) -> bool:
        result = DisconnectGoogleCalendarUseCase(
            connection_repo=self.connection_repo,
            event_link_repo=self.link_repo,
            calendar_client=self.client,
            secret_cipher=self.cipher,
        ).run(DisconnectCalendarCommand(business_id=self.business.id))
        return result.was_connected

    def booking(
        self,
        status: BookingStatus = BookingStatus.CONFIRMED,
        is_sandbox: bool = False,
    ) -> BookingDocument:
        return self.world.add_booking(
            self.business,
            self.table,
            self.contact,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
            status=status,
            is_sandbox=is_sandbox,
        )

    def connection(self) -> CalendarConnectionDocument | None:
        return self.connection_repo.get_by_business(self.business.id)

    def calendar_requests(self) -> list[httpx.Request]:
        """Event requests (the title lookup while connecting is a GET)."""

        return [
            request
            for request in self.google.requests
            if request.url.host == "www.googleapis.com" and request.method != "GET"
        ]


class TestConnection:
    def test_connect_stores_encrypted_tokens_and_only_the_state_hash(self) -> None:
        calendar = CalendarWorld()

        view = calendar.start_view()
        state = CalendarAuthorizationState(
            parse_qs(urlsplit(str(view.authorization_url)).query)["state"][0]
        )
        state_hash = CalendarAuthorizationStateHash(
            hashlib.sha256(str(state).encode()).hexdigest()
        )
        pending = calendar.state_repo.find_by_state_hash(state_hash)
        assert pending is not None
        assert pending.business_id == calendar.business.id
        assert int(view.expires_at) - int(calendar.world.clock.now_microseconds()) == (
            10 * 60 * 1_000_000
        )

        outcome = calendar.complete(state)

        assert outcome.failure is None
        assert outcome.business_id == calendar.business.id
        assert outcome.connection is not None
        connection = calendar.connection()
        assert connection is not None
        assert connection.calendar_id == "primary"
        assert connection.calendar_name == "owner@example.com"
        assert connection.connected_by == calendar.owner_id
        assert "refresh-initial" not in str(connection.encrypted_refresh_token)
        assert calendar.cipher.decrypt(connection.encrypted_refresh_token) == (
            "refresh-initial"
        )
        replayed = calendar.complete(state)
        assert replayed.failure is CalendarConnectionFailure.LINK_EXPIRED
        assert replayed.business_id == calendar.business.id
        assert replayed.connection is None

    def test_only_the_user_who_started_can_complete_the_connection(self) -> None:
        calendar = CalendarWorld()
        state = calendar.start()

        foreign = calendar.complete(state, user_id=UserId())

        assert foreign.failure is CalendarConnectionFailure.LINK_EXPIRED
        assert foreign.business_id is None
        assert calendar.connection() is None
        assert not any(
            request.url.host == "oauth2.googleapis.com"
            for request in calendar.google.requests
        )
        # The state is not used up: the owner can still finish.
        owner = calendar.complete(state)
        assert owner.failure is None
        assert calendar.connection() is not None

    def test_expired_forged_and_refused_authorizations(self) -> None:
        calendar = CalendarWorld()
        state = calendar.start()
        calendar.world.clock.move_to(
            datetime.fromisoformat("2026-10-05T08:11:00+00:00")
        )

        expired = calendar.complete(state)
        assert expired.failure is CalendarConnectionFailure.LINK_EXPIRED
        assert expired.business_id == calendar.business.id

        forged = calendar.complete(CalendarAuthorizationState("forged-state"))
        assert forged.failure is CalendarConnectionFailure.LINK_EXPIRED
        assert forged.business_id is None
        assert calendar.complete(None, code=None).business_id is None

        declined = calendar.complete(
            calendar.start(), code=None, provider_error="access_denied"
        )
        assert declined.failure is CalendarConnectionFailure.ACCESS_DENIED
        assert declined.business_id == calendar.business.id
        odd_error = calendar.complete(
            calendar.start(), code=None, provider_error="server_error"
        )
        assert odd_error.failure is CalendarConnectionFailure.PROVIDER_ERROR

        bad_code = calendar.complete(calendar.start(), code="bad-code")
        assert bad_code.failure is CalendarConnectionFailure.PROVIDER_ERROR

        calendar.google.grants_refresh_token = False
        no_offline = calendar.complete(calendar.start())
        assert no_offline.failure is CalendarConnectionFailure.NO_OFFLINE_ACCESS

        with pytest.raises(NotFoundError):
            calendar.start_view(BusinessId())

        assert calendar.connection() is None

    def test_a_failed_title_lookup_does_not_stop_the_connection(self) -> None:
        calendar = CalendarWorld()
        calendar.google.calendar_name = None

        assert calendar.complete(calendar.start()).failure is None

        connection = calendar.connection()
        assert connection is not None
        assert connection.calendar_name is None

    def test_disconnect_revokes_the_token_and_forgets_events(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        calendar.sync.sync(calendar.booking())

        assert calendar.disconnect()
        assert calendar.google.revoked_tokens == ["refresh-initial"]
        assert calendar.connection() is None
        assert calendar.link_repo.list_by_business(calendar.business.id) == []
        assert not calendar.disconnect()

        calendar.complete(calendar.start())
        calendar.google.failure_status = 503
        assert calendar.disconnect()
        assert calendar.connection() is None


class TestSync:
    def test_event_follows_the_booking_in_the_owner_language(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        booking = calendar.booking()

        calendar.sync.sync(booking)

        link = calendar.link_repo.find_by_booking(calendar.business.id, booking.id)
        assert link is not None
        event = calendar.google.events[str(link.event_id)]
        assert event["summary"] == "Бронь: Nino, гостей: 2"
        assert event["start"] == {
            "dateTime": "2026-10-06T15:00:00Z",
            "timeZone": "Asia/Tbilisi",
        }
        assert "Телефон: +995 555 12 34 56" in str(event["description"])

        booking.starts_at = BookingStartsAtUnixSeconds(int(booking.starts_at) + 3600)
        booking.ends_at = BookingEndsAtUnixSeconds(int(booking.ends_at) + 3600)
        calendar.sync.sync(booking)
        assert calendar.google.events[str(link.event_id)]["start"] == {
            "dateTime": "2026-10-06T16:00:00Z",
            "timeZone": "Asia/Tbilisi",
        }

        booking.status = BookingStatus.CANCELLED
        calendar.sync.sync(booking)
        assert calendar.google.events == {}
        assert (
            calendar.link_repo.find_by_booking(calendar.business.id, booking.id) is None
        )
        assert [request.method for request in calendar.calendar_requests()] == [
            "POST",
            "PATCH",
            "DELETE",
        ]
        # The access token from the code exchange is still valid: no refresh.
        assert calendar.google.refresh_count == 0

    def test_expired_access_token_is_refreshed_once_and_cached(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        calendar.world.clock.move_to(
            datetime.fromisoformat("2026-10-05T10:00:00+00:00")
        )

        calendar.sync.sync(calendar.booking())
        calendar.sync.sync(calendar.booking())

        assert calendar.google.refresh_count == 1
        assert [
            request.headers["authorization"] for request in calendar.calendar_requests()
        ] == ["Bearer access-refreshed-1", "Bearer access-refreshed-1"]
        connection = calendar.connection()
        assert connection is not None
        assert connection.encrypted_access_token is not None
        assert calendar.cipher.decrypt(connection.encrypted_access_token) == (
            "access-refreshed-1"
        )

    def test_nothing_happens_without_connection_for_sandbox_or_finished(self) -> None:
        calendar = CalendarWorld()
        calendar.sync.sync(calendar.booking())
        assert calendar.google.requests == []

        calendar.complete(calendar.start())
        calendar.sync.sync(calendar.booking(is_sandbox=True))
        calendar.sync.sync(calendar.booking(status=BookingStatus.COMPLETED))
        calendar.sync.sync(calendar.booking(status=BookingStatus.CANCELLED))
        assert calendar.calendar_requests() == []

    def test_google_and_storage_failures_never_raise(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        booking = calendar.booking()
        calendar.google.failure_status = 503

        calendar.sync.sync(booking)

        assert (
            calendar.link_repo.find_by_booking(calendar.business.id, booking.id) is None
        )
        connection = calendar.connection()
        assert connection is not None
        assert connection.last_sync_error == (
            "Google Calendar event insert returned HTTP 503 (UNAVAILABLE)."
        )
        assert connection.last_sync_error_at == calendar.world.clock.now_microseconds()
        assert connection.last_synced_at is None
        connection.encrypted_access_token = None
        connection.encrypted_refresh_token = EncryptedChannelSecret("corrupted")
        calendar.connection_repo.save(connection)
        calendar.google.failure_status = None
        requests_before = len(calendar.google.requests)

        calendar.sync.sync(booking)

        assert len(calendar.google.requests) == requests_before
        broken = calendar.connection()
        assert broken is not None
        assert broken.last_sync_error is not None
        assert "corrupted" not in str(broken.last_sync_error)

    def test_a_successful_sync_clears_the_last_error(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())
        calendar.google.failure_status = 401
        calendar.sync.sync(calendar.booking())
        failed = calendar.connection()
        assert failed is not None
        assert failed.last_sync_error is not None

        calendar.google.failure_status = None
        calendar.sync.sync(calendar.booking())

        healed = calendar.connection()
        assert healed is not None
        assert healed.last_sync_error is None
        assert healed.last_sync_error_at is None
        assert healed.last_synced_at == calendar.world.clock.now_microseconds()

    def test_long_provider_errors_are_shortened(self) -> None:
        summary = summarize_sync_failure("x" * 1000)

        assert len(str(summary)) == 300
        assert str(summary).endswith("…")
        assert summarize_sync_failure("  a \n b ") == "a b"

    def test_create_booking_pushes_the_event(self) -> None:
        calendar = CalendarWorld()
        calendar.complete(calendar.start())

        calendar.world.create_booking(calendar.sync).run(
            CreateBookingCommand(
                business_id=calendar.business.id,
                contact_id=calendar.contact.id,
                contact_name=ContactName("Nino"),
                contact_phone_number=E164PhoneNumber("+995555123456"),
                date=LocalDate("2026-10-07"),
                time=LocalTimeOfDay("20:00"),
                party_size=PartySize(2),
                source_channel=ChannelKind.TELEGRAM,
                language=LanguageTag("ka"),
            )
        )

        assert len(calendar.google.events) == 1
        event = next(iter(calendar.google.events.values()))
        assert event["end"] == {
            "dateTime": "2026-10-07T18:00:00Z",
            "timeZone": "Asia/Tbilisi",
        }
