from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.bookings.booleans import IsCalendarAuthorizationStateConsumed
from app.schemas.typings.bookings.prefixed_id import (
    BookingId,
    CalendarAuthorizationStateId,
    CalendarConnectionId,
    CalendarEventLinkId,
)
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationStateHash,
    CalendarEventId,
    ExternalCalendarId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.users.prefixed_id import UserId


class CalendarConnectionDocument(BaseDocument):
    """
    Google Calendar connected by the owner of a business (one per business).

    Tokens are stored only encrypted with the platform key. The access token
    is a cache: it is refreshed from the refresh token when it expires.
    """

    id: CalendarConnectionId = Field(default_factory=CalendarConnectionId)
    business_id: BusinessId
    calendar_id: ExternalCalendarId
    encrypted_refresh_token: EncryptedChannelSecret
    encrypted_access_token: EncryptedChannelSecret | None = None
    access_token_expires_at: Microseconds | None = None
    connected_by: UserId


class CalendarAuthorizationStateDocument(BaseDocument):
    """
    Pending OAuth authorization started by an owner.

    The random `state` sent to the provider is stored only as a hash and can
    be used once before it expires; it binds the callback to the business.
    """

    id: CalendarAuthorizationStateId = Field(
        default_factory=CalendarAuthorizationStateId
    )
    business_id: BusinessId
    user_id: UserId
    state_hash: CalendarAuthorizationStateHash
    expires_at: Microseconds
    is_consumed: IsCalendarAuthorizationStateConsumed = False


class CalendarEventLinkDocument(BaseDocument):
    """Calendar event created for a booking, so changes update the same event."""

    id: CalendarEventLinkId = Field(default_factory=CalendarEventLinkId)
    business_id: BusinessId
    booking_id: BookingId
    calendar_id: ExternalCalendarId
    event_id: CalendarEventId
