"""A Tbilisi restaurant whose owner connects Google Calendar, over fakes."""

from urllib.parse import parse_qs, urlsplit

import httpx

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
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.dto.calendar import CalendarConnectionOutcome
from app.schemas.dto.operations.calendar_connection import (
    CalendarConnectUrlView,
    CompleteCalendarConnectionCommand,
    DisconnectCalendarCommand,
    StartCalendarConnectionCommand,
)
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationCode,
    CalendarAuthorizationState,
    CalendarProviderErrorCode,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
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
