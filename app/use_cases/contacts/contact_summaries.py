"""Customer activity shared by the contact list and the contact page."""

from typed_time_provider import Microseconds

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.contacts import ContactActivity, ContactSummaryView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.booleans import (
    HasContactTestActivity,
    IsContactPhoneVerified,
)
from app.schemas.typings.contacts.constrained_integers import (
    ContactBookingCount,
    ContactConversationCount,
    ContactLeadCount,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


def collect_contact_activity(
    business_id: BusinessId,
    conversation_repo: ConversationRepoContract,
    booking_repo: BookingRepoContract,
    lead_repo: LeadRepoContract,
) -> dict[ContactId, ContactActivity]:
    """Records of every customer of a business, keyed by contact id."""

    conversations: dict[ContactId, list[ConversationDocument]] = {}
    bookings: dict[ContactId, list[BookingDocument]] = {}
    leads: dict[ContactId, list[LeadDocument]] = {}
    tested: set[ContactId] = set()
    for conversation in conversation_repo.list_by_business(business_id):
        if conversation.is_sandbox:
            tested.add(conversation.contact_id)
        else:
            conversations.setdefault(conversation.contact_id, []).append(conversation)

    for booking in booking_repo.list_by_business(business_id):
        if booking.is_sandbox:
            tested.add(booking.contact_id)
        else:
            bookings.setdefault(booking.contact_id, []).append(booking)

    for lead in lead_repo.list_by_business(business_id):
        if lead.is_sandbox:
            tested.add(lead.contact_id)
        else:
            leads.setdefault(lead.contact_id, []).append(lead)

    return {
        contact_id: ContactActivity(
            conversations=conversations.get(contact_id, []),
            bookings=bookings.get(contact_id, []),
            leads=leads.get(contact_id, []),
            has_test_activity=HasContactTestActivity(contact_id in tested),
        )
        for contact_id in {*conversations, *bookings, *leads, *tested}
    }


def is_test_contact(contact: ContactDocument, activity: ContactActivity) -> bool:
    """
    A "customer" made only by the owner's test chat or the autotests: no
    real records, and test records or only test-chat identities.
    """

    if activity.conversations or activity.bookings or activity.leads:
        return False

    identities: list[ChannelKind] = [
        identity.channel for identity in contact.channel_identities
    ]
    return activity.has_test_activity or (
        identities != []
        and all(channel is ChannelKind.OWNER_TEST for channel in identities)
    )


def summarize_contact(
    contact: ContactDocument,
    activity: ContactActivity,
) -> ContactSummaryView:
    """
    The list row of a customer; test chats are left out of the counts. The
    channels are those the customer wrote, called or booked through.
    """

    channels: set[ChannelKind] = {
        identity.channel
        for identity in contact.channel_identities
        if identity.channel is not ChannelKind.OWNER_TEST
    } | {
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
    if contact.erased_at is not None:
        moments.append(contact.erased_at)

    phone_number: E164PhoneNumber | None = (
        contact.verified_phone_number or contact.phone_number
    )
    return ContactSummaryView(
        id=contact.id,
        name=contact.name,
        phone_number=phone_number,
        is_phone_verified=IsContactPhoneVerified(
            contact.verified_phone_number is not None
        ),
        language=contact.language,
        channels=sorted(channels, key=lambda channel: channel.value),
        conversation_count=ContactConversationCount(len(activity.conversations)),
        booking_count=ContactBookingCount(len(activity.bookings)),
        lead_count=ContactLeadCount(len(activity.leads)),
        first_seen_at=contact.created_at,
        last_activity_at=max(moments),
        erased_at=contact.erased_at,
    )
