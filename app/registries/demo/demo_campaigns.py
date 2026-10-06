"""
The return visits of a demo business: the campaign on with its niche's
rule, and the messages of the last weeks. A guest who came back after an
invitation booked again (that booking counts as the campaign's); others
were invited and have not answered yet; a guest who said STOP was skipped.
"""

from collections.abc import Sequence
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.registries.demo.demo_waitlist import channel_of
from app.registries.niches.rebooking_rule_catalog import NICHE_REBOOKING_RULES
from app.schemas.constants.bookings import BookingOrigin, BookingStatus
from app.schemas.constants.campaigns import (
    CampaignMessageStatus,
    CampaignSkipReason,
    RebookingRuleKind,
)
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import (
    CampaignMessageDocument,
    CampaignSettingsDocument,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.utilities.campaigns.campaign_keys import (
    campaign_message_id_of,
    campaign_month_of,
    campaign_settings_id_of,
)
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
DAY: int = 24 * 60 * 60 * MICROSECONDS_PER_SECOND
# Invitations without an answer yet, and returns, at most.
INVITED_LIMIT: int = 3
RETURNED_LIMIT: int = 2
KEPT_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.CONFIRMED, BookingStatus.COMPLETED}
)


def build_demo_campaign_settings(
    business: BusinessDocument, now: Microseconds
) -> CampaignSettingsDocument:
    """The campaign on, with the niche's own rule and the default cap."""

    rule = next(
        rule for rule in NICHE_REBOOKING_RULES if rule.niche_key is business.niche_key
    )
    return CampaignSettingsDocument(
        id=campaign_settings_id_of(business.id),
        business_id=business.id,
        is_enabled=True,
        rule_kind=rule.rule_kind,
        delay_days=rule.delay_days,
        created_at=business.created_at,
        updated_at=now,
    )


def build_demo_campaign_messages(
    business: BusinessDocument,
    bookings: Sequence[BookingDocument],
    contacts: Sequence[ContactDocument],
    now: Microseconds,
) -> list[CampaignMessageDocument]:
    """The messages; a return is marked on the booking it brought."""

    zone: ZoneInfo = load_time_zone(business.timezone)
    by_id: dict[ContactId, ContactDocument] = {item.id: item for item in contacts}
    visits: dict[ContactId, list[BookingDocument]] = {}
    for booking in sorted(bookings, key=lambda item: int(item.starts_at)):
        if (
            booking.status in KEPT_STATUSES
            and not booking.is_sandbox
            and booking.contact_id in by_id
            and int(booking.created_at) < int(now)
        ):
            visits.setdefault(booking.contact_id, []).append(booking)

    messages: list[CampaignMessageDocument] = []
    returned: int = 0
    invited: int = 0
    for contact_id, kept in visits.items():
        contact: ContactDocument = by_id[contact_id]
        later = [item for item in kept[1:] if item.origin is None]
        if contact.opted_out_channels:
            messages.append(skipped(business, kept[0], contact, zone, now))
        elif later and returned < RETURNED_LIMIT:
            messages.append(came_back(business, kept[0], later[0], contact, zone))
            returned += 1
        elif not later and invited < INVITED_LIMIT:
            sent_at = Microseconds(int(now) - (invited + 1) * 2 * DAY)
            messages.append(message_of(business, kept[0], contact, zone, sent_at, now))
            invited += 1

    return messages


def came_back(
    business: BusinessDocument,
    visit: BookingDocument,
    follow_up: BookingDocument,
    contact: ContactDocument,
    zone: ZoneInfo,
) -> CampaignMessageDocument:
    """An invitation the guest answered by booking again."""

    follow_up.origin = BookingOrigin.CAMPAIGN
    sent_at = Microseconds(int(follow_up.created_at) - 2 * DAY)
    message = message_of(business, visit, contact, zone, sent_at, follow_up.created_at)
    message.status = CampaignMessageStatus.BOOKED
    message.booking_id = follow_up.id
    message.booked_at = follow_up.created_at
    return message


def skipped(
    business: BusinessDocument,
    visit: BookingDocument,
    contact: ContactDocument,
    zone: ZoneInfo,
    now: Microseconds,
) -> CampaignMessageDocument:
    """A guest who said STOP: never written to."""

    message = message_of(business, visit, contact, zone, now, now)
    message.status = CampaignMessageStatus.SKIPPED
    message.skip_reason = CampaignSkipReason.OPTED_OUT
    message.channel = None
    message.sent_at = None
    return message


def message_of(
    business: BusinessDocument,
    visit: BookingDocument,
    contact: ContactDocument,
    zone: ZoneInfo,
    sent_at: Microseconds,
    updated_at: Microseconds,
) -> CampaignMessageDocument:
    rule_kind = RebookingRuleKind.REBOOK
    return CampaignMessageDocument(
        id=campaign_message_id_of(business.id, rule_kind, visit.id),
        business_id=business.id,
        contact_id=contact.id,
        rule_kind=rule_kind,
        anchor_booking_id=visit.id,
        status=CampaignMessageStatus.SENT,
        month=campaign_month_of(sent_at, zone),
        language=visit.language or contact.language or business.default_language,
        channel=channel_of(contact),
        sent_at=sent_at,
        created_at=sent_at,
        updated_at=updated_at,
    )
