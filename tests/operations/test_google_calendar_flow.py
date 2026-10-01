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
)
from app.repositories.calendar_repositories import (
    CalendarAuthorizationStateRepository,
    CalendarConnectionRepository,
    CalendarEventLinkRepository,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.dto.operations import (
    CalendarConnectUrlView,
    CompleteCalendarConnectionCommand,
    DisconnectCalendarCommand,
    StartCalendarConnectionCommand,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    NotFoundError,
    ValidationFailedError,
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
from tests.operations.builders import OperationsWorld
from tests.operations.fake_google import FakeGoogle
from tests.operations.fakes import ReversingSecretCipher


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
        state: CalendarAuthorizationState,
        code: str = "good-code",
    ) -> None:
        CompleteGoogleCalendarConnectionUseCase(
            authorization_state_repo=self.state_repo,
            connection_repo=self.connection_repo,
            calendar_client=self.client,
            secret_cipher=self.cipher,
            wall_clock=self.world.clock.wall_clock,
        ).run(
            CompleteCalendarConnectionCommand(
                state=state, code=CalendarAuthorizationCode(code)
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
        return [
            request
            for request in self.google.requests
            if request.url.host == "www.googleapis.com"
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

        calendar.complete(state)

        connection = calendar.connection()
        assert connection is not None
        assert connection.calendar_id == "primary"
        assert connection.connected_by == calendar.owner_id
        assert "refresh-initial" not in str(connection.encrypted_refresh_token)
        assert calendar.cipher.decrypt(connection.encrypted_refresh_token) == (
            "refresh-initial"
        )
        with pytest.raises(ValidationFailedError, match="already used"):
            calendar.complete(state)

    def test_expired_forged_and_refused_authorizations(self) -> None:
        calendar = CalendarWorld()
        state = calendar.start()
        calendar.world.clock.move_to(
            datetime.fromisoformat("2026-10-05T08:11:00+00:00")
        )

        with pytest.raises(ValidationFailedError, match="expired"):
            calendar.complete(state)

        with pytest.raises(ValidationFailedError):
            calendar.complete(CalendarAuthorizationState("forged-state"))

        with pytest.raises(ExternalServiceError, match="invalid_grant"):
            calendar.complete(calendar.start(), code="bad-code")

        calendar.google.grants_refresh_token = False
        with pytest.raises(ExternalServiceError, match="offline access"):
            calendar.complete(calendar.start())

        with pytest.raises(NotFoundError):
            calendar.start_view(BusinessId())

        assert calendar.connection() is None

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
        connection.encrypted_access_token = None
        connection.encrypted_refresh_token = EncryptedChannelSecret("corrupted")
        calendar.connection_repo.save(connection)
        calendar.google.failure_status = None
        requests_before = len(calendar.google.requests)

        calendar.sync.sync(booking)

        assert len(calendar.google.requests) == requests_before

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
