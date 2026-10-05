"""A customer's row in the list and the head of their page."""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.contacts import (
    ContactActivity,
    ContactActivityTotals,
    ContactSummaryView,
)
from app.schemas.typings.contacts.booleans import IsContactPhoneVerified
from app.schemas.typings.contacts.constrained_integers import (
    ContactBookingCount,
    ContactConversationCount,
    ContactLeadCount,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


def summarize_contact_row(
    contact: ContactDocument,
    totals: ContactActivityTotals | None,
) -> ContactSummaryView:
    """
    The list row of a customer from the counts of a page (test chats left
    out). The channels are those the customer wrote, called or booked
    through; the last activity is the latest of their records, their own
    last-seen moment and their erasure.
    """

    counted: ContactActivityTotals = totals or ContactActivityTotals()
    moments: list[Microseconds] = [
        moment
        for moment in (
            contact.created_at,
            contact.last_seen_at,
            contact.erased_at,
            counted.latest_at,
        )
        if moment is not None
    ]
    return build_view(
        contact,
        channels=set(counted.channels),
        counts=(
            counted.conversation_count,
            counted.booking_count,
            counted.lead_count,
        ),
        last_activity_at=max(moments),
    )


def summarize_contact(
    contact: ContactDocument,
    activity: ContactActivity,
) -> ContactSummaryView:
    """The head of one customer's page from their records (test chats left out)."""

    channels: set[ChannelKind] = {
        *(conversation.channel for conversation in activity.conversations),
        *(booking.source_channel for booking in activity.bookings),
        *(lead.source_channel for lead in activity.leads),
    }
    moments: list[Microseconds] = [
        contact.created_at,
        *(conversation.last_message_at for conversation in activity.conversations),
        *(booking.created_at for booking in activity.bookings),
        *(lead.created_at for lead in activity.leads),
    ]
    for moment in (contact.last_seen_at, contact.erased_at):
        if moment is not None:
            moments.append(moment)

    return build_view(
        contact,
        channels=channels,
        counts=(
            ContactConversationCount(len(activity.conversations)),
            ContactBookingCount(len(activity.bookings)),
            ContactLeadCount(len(activity.leads)),
        ),
        last_activity_at=max(moments),
    )


def build_view(
    contact: ContactDocument,
    channels: set[ChannelKind],
    counts: tuple[ContactConversationCount, ContactBookingCount, ContactLeadCount],
    last_activity_at: Microseconds,
) -> ContactSummaryView:
    phone_number: E164PhoneNumber | None = (
        contact.verified_phone_number or contact.phone_number
    )
    all_channels: set[ChannelKind] = {
        identity.channel
        for identity in contact.channel_identities
        if identity.channel is not ChannelKind.OWNER_TEST
    } | {channel for channel in channels if channel is not ChannelKind.OWNER_TEST}
    return ContactSummaryView(
        id=contact.id,
        name=contact.name,
        phone_number=phone_number,
        is_phone_verified=IsContactPhoneVerified(
            contact.verified_phone_number is not None
        ),
        language=contact.language,
        channels=sorted(all_channels, key=lambda channel: channel.value),
        conversation_count=counts[0],
        booking_count=counts[1],
        lead_count=counts[2],
        first_seen_at=contact.created_at,
        last_activity_at=last_activity_at,
        erased_at=contact.erased_at,
        opted_out_channels=list(contact.opted_out_channels),
    )
