"""
What every request of a guest's manage page shares: counting it against
the public limits, finding the booking the link names as it still is, and
the page's view of it (no contact details of the guest: anyone holding the
link sees the page).
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.booking_links import BookingManageTokenSignerContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.bookings import ManagedBookingRefusalCode
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.sharing import ShareLinkKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.booking_manage import (
    BookingManageClaims,
    ManagedBookingAction,
    ManagedBookingView,
)
from app.schemas.dto.channels.widget import WidgetContactLinkView
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.bookings.constrained_strings import BookingManageToken
from app.schemas.typings.platform.constrained_strings import (
    CabinetBaseUrl,
    ErrorReasonCode,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.sharing.constrained_strings import ShareLinkUrl
from app.use_cases.bookings.guest_booking import GuestBooking, GuestBookingReader
from app.utilities.bookings.booking_manage_links import (
    choose_maps_url,
    manage_link_expiry,
)
from app.utilities.bookings.manage_rate_limits import (
    ManageRateLimits,
    refuse_too_frequent_manage_requests,
)
from app.utilities.channels.channel_links import build_hosted_chat_url
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    minute_of_day,
    to_local_date,
    to_local_moment,
    to_time_of_day,
)
from app.utilities.sharing.share_links import (
    SHARE_LINK_KIND_OF,
    build_contact_links,
    business_address,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
CHANGED_MESSAGE: str = (
    "This booking was changed after the link was sent; open the latest confirmation."
)
NOT_ACTIVE_MESSAGE: str = "This booking can no longer be changed."
STARTED_MESSAGE: str = "This booking has started and can no longer be changed here."


def refusal(code: ManagedBookingRefusalCode, message: str) -> list[ErrorReason]:
    return [
        ErrorReason(
            code=ErrorReasonCode(code.value),
            message=ErrorReasonMessage(message),
        )
    ]


@dataclass(frozen=True)
class ManagedBookingPages:
    """The shared steps of the manage page's requests (module docstring)."""

    guest_bookings: GuestBookingReader
    channel_repo: ChannelRepoContract
    link_signer: BookingManageTokenSignerContract
    rate_limits: RequestRateLimitRegistryContract
    wall_clock: WallClock[Microseconds]
    cabinet_base_url: CabinetBaseUrl | None

    def refuse_too_frequent(
        self,
        action: ManagedBookingAction,
        limits: ManageRateLimits,
    ) -> None:
        refuse_too_frequent_manage_requests(
            self.rate_limits,
            limits,
            action.claims.booking_id,
            action.client_ip_address,
            self.wall_clock.now_unix(),
        )

    def current(self, claims: BookingManageClaims) -> GuestBooking:
        """
        The booking as it still is; NotFoundError (`booking_changed`) when it
        is gone or was moved after the link was issued.
        """

        guest_booking: GuestBooking | None = self.guest_bookings.read(
            claims.business_id, claims.booking_id
        )
        if (
            guest_booking is None
            or guest_booking.booking.is_sandbox
            or guest_booking.booking.starts_at != claims.booking_version
        ):
            raise NotFoundError(
                CHANGED_MESSAGE,
                reasons=refusal(
                    ManagedBookingRefusalCode.BOOKING_CHANGED, CHANGED_MESSAGE
                ),
            )

        return guest_booking

    def refuse_unchangeable(self, booking: BookingDocument) -> None:
        """
        Raises:
            ConflictError: the booking is no longer active (`not_active`) or
                has started (`already_started`).
        """

        if booking.status not in BLOCKING_BOOKING_STATUSES:
            raise ConflictError(
                NOT_ACTIVE_MESSAGE,
                reasons=refusal(
                    ManagedBookingRefusalCode.NOT_ACTIVE, NOT_ACTIVE_MESSAGE
                ),
            )

        if not self._is_upcoming(booking):
            raise ConflictError(
                STARTED_MESSAGE,
                reasons=refusal(
                    ManagedBookingRefusalCode.ALREADY_STARTED, STARTED_MESSAGE
                ),
            )

    def token_for(self, booking: BookingDocument) -> BookingManageToken:
        """A fresh link token of the booking as it is now."""

        return self.link_signer.sign(
            BookingManageClaims(
                business_id=booking.business_id,
                booking_id=booking.id,
                booking_version=booking.starts_at,
                expires_at=manage_link_expiry(booking.ends_at),
            )
        )

    def view(
        self,
        guest_booking: GuestBooking,
        token: BookingManageToken,
    ) -> ManagedBookingView:
        booking: BookingDocument = guest_booking.booking
        zone = load_time_zone(guest_booking.business.timezone)
        starts = to_local_moment(int(booking.starts_at), zone)
        ends = to_local_moment(int(booking.ends_at), zone)
        profile = guest_booking.profile
        is_changeable: bool = (
            booking.status in BLOCKING_BOOKING_STATUSES and self._is_upcoming(booking)
        )
        return ManagedBookingView(
            token=token,
            business_name=guest_booking.business.name,
            status=booking.status,
            booking_unit=guest_booking.booking_unit,
            date=to_local_date(starts.date()),
            time=to_time_of_day(minute_of_day(starts)),
            end_date=to_local_date(ends.date()),
            end_time=to_time_of_day(minute_of_day(ends)),
            timezone=guest_booking.business.timezone,
            party_size=booking.party_size,
            service_title=guest_booking.service_title,
            address=None
            if profile is None or profile.address is None
            else profile.address.text,
            maps_url=None if profile is None else choose_maps_url(profile.address),
            phone_number=(
                None if profile is None else profile.contacts.public_phone_number
            ),
            cancellation_policy=(
                None
                if profile is None or profile.booking_rules is None
                else profile.booking_rules.cancellation_policy
            ),
            language=booking.language or guest_booking.business.default_language,
            chat_links=self._chat_links(guest_booking),
            can_cancel=is_changeable,
            can_reschedule=is_changeable,
            is_over=self._now_seconds() >= int(booking.ends_at),
        )

    def _chat_links(self, guest_booking: GuestBooking) -> list[WidgetContactLinkView]:
        """
        Ways to write to the business: the chat the booking was made in
        first, then the hosted chat page and the other messengers and a call.
        """

        business = guest_booking.business
        channels: list[ChannelDocument] = self.channel_repo.list_by_business(
            business.id
        )
        links: list[WidgetContactLinkView] = build_contact_links(
            channels, guest_booking.profile
        )
        has_web_chat: bool = any(
            channel.kind is ChannelKind.WEB_CHAT
            and channel.status is ChannelStatus.CONNECTED
            for channel in channels
        )
        if has_web_chat and self.cabinet_base_url is not None:
            links.insert(
                0,
                WidgetContactLinkView(
                    kind=ShareLinkKind.HOSTED_CHAT,
                    url=ShareLinkUrl(
                        build_hosted_chat_url(
                            self.cabinet_base_url, business_address(business)
                        )
                    ),
                ),
            )

        source = guest_booking.booking.source_channel
        first: ShareLinkKind = (
            ShareLinkKind.HOSTED_CHAT
            if source is ChannelKind.WEB_CHAT
            else SHARE_LINK_KIND_OF.get(source, ShareLinkKind.HOSTED_CHAT)
        )
        return sorted(links, key=lambda link: link.kind is not first)

    def _is_upcoming(self, booking: BookingDocument) -> bool:
        return self._now_seconds() < int(booking.starts_at)

    def _now_seconds(self) -> int:
        return int(self.wall_clock.now_unix()) // MICROSECONDS_PER_SECOND
