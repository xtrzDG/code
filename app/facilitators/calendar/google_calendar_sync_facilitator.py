import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.operations import (
    BookingCalendarSyncFacilitatorContract,
    CalendarConnectionRepoContract,
    CalendarEventLinkRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.repositories import (
    BusinessRepoContract,
    ContactRepoContract,
    ResourceRepoContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.calendar import (
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations import (
    CalendarEventDraft,
    CalendarEventText,
    CalendarEventTextInput,
    CalendarTokenGrant,
)
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarEventId,
    CalendarRefreshToken,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    RawPhoneNumberInput,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import (
    MICROSECONDS_PER_SECOND,
    load_time_zone,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
# Refresh a cached access token this long before Google expires it.
ACCESS_TOKEN_SAFETY_SECONDS: int = 60


class GoogleCalendarSyncFacilitator(BookingCalendarSyncFacilitatorContract):
    """
    Mirrors real bookings in the business's Google Calendar.

    Active bookings (pending, confirmed) create an event or update the linked
    one; a cancelled booking deletes it; completed and no-show bookings keep
    theirs. The event is described in the owner's language. Sandbox bookings
    and businesses without a connection are skipped. Every failure is logged
    and swallowed: the calendar never breaks a booking.
    """

    def __init__(
        self,
        connection_repo: CalendarConnectionRepoContract,
        event_link_repo: CalendarEventLinkRepoContract,
        business_repo: BusinessRepoContract,
        resource_repo: ResourceRepoContract,
        contact_repo: ContactRepoContract,
        calendar_client: GoogleCalendarClientContract,
        secret_cipher: SecretCipherAdapterContract,
        phone_number_parser: PhoneNumberParserContract,
        event_text_transformer: TransformerContract[
            CalendarEventTextInput, CalendarEventText
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._event_link_repo: CalendarEventLinkRepoContract = event_link_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._event_text_transformer: TransformerContract[
            CalendarEventTextInput, CalendarEventText
        ] = event_text_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def sync(self, booking: BookingDocument) -> None:
        if booking.is_sandbox:
            return

        try:
            self._sync(booking)
        except ApplicationError as error:
            LOGGER.warning("Calendar sync of booking %s failed: %s", booking.id, error)
        except Exception:  # noqa: BLE001 - the calendar must never break a booking
            LOGGER.exception("Calendar sync of booking %s raised.", booking.id)

    def _sync(self, booking: BookingDocument) -> None:
        connection: CalendarConnectionDocument | None = (
            self._connection_repo.get_by_business(booking.business_id)
        )
        if connection is None:
            return

        link: CalendarEventLinkDocument | None = self._event_link_repo.find_by_booking(
            booking.business_id, booking.id
        )
        if booking.status in BLOCKING_BOOKING_STATUSES:
            self._upsert_event(connection, booking, link)
        elif booking.status is BookingStatus.CANCELLED and link is not None:
            self._calendar_client.delete_event(
                self._access_token(connection), link.calendar_id, link.event_id
            )
            self._event_link_repo.delete_by_booking(booking.business_id, booking.id)

    def _upsert_event(
        self,
        connection: CalendarConnectionDocument,
        booking: BookingDocument,
        link: CalendarEventLinkDocument | None,
    ) -> None:
        business: BusinessDocument | None = self._business_repo.get(booking.business_id)
        if business is None:
            return

        draft: CalendarEventDraft = self._draft(business, booking)
        access_token: CalendarAccessToken = self._access_token(connection)
        if link is not None:
            self._calendar_client.patch_event(
                access_token, link.calendar_id, link.event_id, draft
            )
            return

        event_id: CalendarEventId = self._calendar_client.insert_event(
            access_token, connection.calendar_id, draft
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._event_link_repo.save(
            CalendarEventLinkDocument(
                business_id=booking.business_id,
                booking_id=booking.id,
                calendar_id=connection.calendar_id,
                event_id=event_id,
                created_at=now,
                updated_at=now,
            )
        )

    def _draft(
        self,
        business: BusinessDocument,
        booking: BookingDocument,
    ) -> CalendarEventDraft:
        view: BookingView = build_booking_view(
            booking,
            business.timezone,
            load_time_zone(business.timezone),
            self._resource_repo.get(business.id, booking.resource_id),
            self._contact_repo.get(business.id, booking.contact_id),
        )
        text: CalendarEventText = self._event_text_transformer.transform(
            CalendarEventTextInput(
                booking=view,
                contact_phone_display=self._display_phone(view.contact_phone_number),
                language=business.owner_language,
            )
        )
        return CalendarEventDraft(
            title=text.title,
            description=text.description,
            starts_at=booking.starts_at,
            ends_at=booking.ends_at,
            timezone=business.timezone,
        )

    def _display_phone(
        self,
        phone_number: E164PhoneNumber | None,
    ) -> FormattedPhoneNumber | None:
        if phone_number is None:
            return None

        try:
            return self._phone_number_parser.parse(
                RawPhoneNumberInput(str(phone_number)), None
            ).international_format
        except InvalidPhoneNumberError:
            return FormattedPhoneNumber(str(phone_number))

    def _access_token(
        self,
        connection: CalendarConnectionDocument,
    ) -> CalendarAccessToken:
        """Cached access token, refreshed (and re-cached) when about to expire."""

        now: Microseconds = self._wall_clock.now_unix()
        safety_margin: int = ACCESS_TOKEN_SAFETY_SECONDS * MICROSECONDS_PER_SECOND
        if (
            connection.encrypted_access_token is not None
            and connection.access_token_expires_at is not None
            and int(connection.access_token_expires_at) > int(now) + safety_margin
        ):
            return CalendarAccessToken(
                str(self._secret_cipher.decrypt(connection.encrypted_access_token))
            )

        refresh_token = CalendarRefreshToken(
            str(self._secret_cipher.decrypt(connection.encrypted_refresh_token))
        )
        grant: CalendarTokenGrant = self._calendar_client.refresh_access_token(
            refresh_token
        )
        connection.encrypted_access_token = self._secret_cipher.encrypt(
            ChannelSecret(str(grant.access_token))
        )
        connection.access_token_expires_at = Microseconds(
            int(now) + int(grant.expires_in) * MICROSECONDS_PER_SECOND
        )
        if grant.refresh_token is not None:
            connection.encrypted_refresh_token = self._secret_cipher.encrypt(
                ChannelSecret(str(grant.refresh_token))
            )

        connection.updated_at = now
        self._connection_repo.save(connection)
        return grant.access_token
