"""Which bookings get a reminder, through which identities, in which language."""

from zoneinfo import ZoneInfo

from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.profiles.strings import CancellationPolicyText
from app.use_cases.bookings.booking_support import booking_unit_of
from app.utilities.scheduling.booking_views import build_booking_view

# Channels a reminder can be written to, best first after the booking's own
# channel: Telegram has no messaging window and costs nothing; WhatsApp is
# where most customers are.
MESSAGING_CHANNELS: tuple[ChannelKind, ...] = (
    ChannelKind.TELEGRAM,
    ChannelKind.WHATSAPP,
    ChannelKind.MESSENGER,
    ChannelKind.INSTAGRAM,
)


def sends_reminders(business: BusinessDocument) -> bool:
    """Paused businesses and leads-only service send no reminders."""

    return (
        business.status is not BusinessStatus.PAUSED
        and business.service_mode is ServiceMode.FULL
    )


def is_reminder_due(
    booking: BookingDocument,
    now_seconds: int,
    window_end_seconds: int,
) -> bool:
    """Confirmed, real, not yet reminded, starting within the window."""

    return (
        booking.status is BookingStatus.CONFIRMED
        and not booking.is_sandbox
        and booking.reminder_sent_at is None
        and now_seconds < int(booking.starts_at) <= window_end_seconds
    )


def choose_reminder_identities(
    contact: ContactDocument,
    source_channel: ChannelKind,
) -> list[ChannelIdentity]:
    """
    Messaging identities to try, best first: the booking's own channel, then
    the other messengers the customer is known in. Phone and web chat cannot
    carry a message later, so they are never used.
    """

    preferred_channels: list[ChannelKind] = [
        channel
        for channel in (source_channel, *MESSAGING_CHANNELS)
        if channel in MESSAGING_CHANNELS
    ]
    identities: list[ChannelIdentity] = []
    for channel in preferred_channels:
        for identity in contact.channel_identities:
            if identity.channel is channel and identity not in identities:
                identities.append(identity)

    return identities


def choose_reminder_language(
    contact: ContactDocument,
    business: BusinessDocument,
) -> LanguageTag:
    """The customer's language when known, else the business default."""

    if contact.language is not None:
        return contact.language

    return business.default_language


def read_cancellation_policy(
    business_profile_repo: BusinessProfileRepoContract,
    business: BusinessDocument,
) -> CancellationPolicyText | None:
    """The cancellation policy of the profile's booking rules, if any."""

    profile: BusinessProfileDocument | None = business_profile_repo.get_by_business(
        business.id
    )
    if profile is None or profile.booking_rules is None:
        return None

    return profile.booking_rules.cancellation_policy


def build_reminder_message(
    business: BusinessDocument,
    zone: ZoneInfo,
    cancellation_policy: CancellationPolicyText | None,
    booking: BookingDocument,
    resource: ResourceDocument | None,
    contact: ContactDocument,
) -> BookingMessageInput:
    """What the reminder text is made of, in the customer's language."""

    return BookingMessageInput(
        business_name=business.name,
        booking=build_booking_view(
            booking,
            business.timezone,
            zone,
            resource,
            contact,
        ),
        booking_unit=booking_unit_of(resource),
        language=choose_reminder_language(contact, business),
        cancellation_policy=cancellation_policy,
    )
