"""
The return visits of a demo business: the campaign on with its niche's
rule, and the messages of the last weeks, each following a visit 30 days
before it. Two guests came back after their invitation (their booking of
the last days counts as the campaign's); others were invited and have not
answered yet; a guest who said STOP is skipped.
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
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.utilities.campaigns.campaign_keys import (
    campaign_message_id_of,
    campaign_month_of,
    campaign_settings_id_of,
)
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
DAY: int = 24 * 60 * 60 * MICROSECONDS_PER_SECOND
DAY_SECONDS: int = 24 * 60 * 60
# Invitations without an answer yet, and returns, at most (a quiet guest
# who said STOP is skipped).
INVITED_LIMIT: int = 3
RETURNED_LIMIT: int = 2
# A return answers an invitation after a visit this long before it; a
# booking of the last days is one.
EARLIER_VISIT_DAYS: int = 37
RECENT_DAYS: int = 10
REBOOK_AFTER_DAYS: int = 30
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
    bookings: list[BookingDocument],
    contacts: Sequence[ContactDocument],
    now: Microseconds,
) -> list[CampaignMessageDocument]:
    """
    The messages; the earlier visits they follow are added to `bookings`
    (the demo month holds one visit a guest), and a return is marked on the
    booking it brought.
    """

    zone: ZoneInfo = load_time_zone(business.timezone)
    by_id: dict[ContactId, ContactDocument] = {item.id: item for item in contacts}
    kept: list[BookingDocument] = sorted(
        (
            booking
            for booking in bookings
            if booking.status in KEPT_STATUSES
            and not booking.is_sandbox
            and booking.contact_id in by_id
            and int(booking.created_at) < int(now)
        ),
        key=lambda booking: int(booking.created_at),
        reverse=True,
    )
    if not kept:
        return []

    messages: list[CampaignMessageDocument] = []
    returning: list[BookingDocument] = [
        booking
        for booking in kept
        if booking.origin is None
        and int(now) - int(booking.created_at) <= RECENT_DAYS * DAY
        and not by_id[booking.contact_id].opted_out_channels
    ][:RETURNED_LIMIT]
    for booking in returning:
        earlier = earlier_visit(booking, booking.contact_id, booking.starts_at)
        bookings.append(earlier)
        messages.append(
            came_back(business, earlier, booking, by_id[booking.contact_id], zone)
        )

    visited = {booking.contact_id for booking in kept}
    quiet = [
        contact
        for contact in contacts
        if contact.id not in visited
        and contact.name is not None
        and contact.erased_at is None
        and not contact.is_test_only
    ][: INVITED_LIMIT + 1]
    for index, contact in enumerate(quiet):
        visit_start = BookingStartsAtUnixSeconds(
            int(now) // MICROSECONDS_PER_SECOND - (33 + 2 * index) * DAY_SECONDS
        )
        earlier = earlier_visit(kept[0], contact.id, visit_start, days_before=0)
        bookings.append(earlier)
        sent_at = Microseconds(
            int(earlier.ends_at) * MICROSECONDS_PER_SECOND + REBOOK_AFTER_DAYS * DAY
        )
        if contact.opted_out_channels:
            messages.append(skipped(business, earlier, contact, zone, sent_at))
        elif index < INVITED_LIMIT:
            messages.append(
                message_of(business, earlier, contact, zone, sent_at, sent_at)
            )

    return messages


def earlier_visit(
    model: BookingDocument,
    contact_id: ContactId,
    starts_at: BookingStartsAtUnixSeconds,
    days_before: int = EARLIER_VISIT_DAYS,
) -> BookingDocument:
    """A visit like `model` (table, party, value) some days before `starts_at`."""

    length: int = int(model.ends_at) - int(model.starts_at)
    starts: int = int(starts_at) - days_before * DAY_SECONDS
    made = Microseconds((starts - 2 * DAY_SECONDS) * MICROSECONDS_PER_SECOND)
    return BookingDocument(
        business_id=model.business_id,
        resource_id=model.resource_id,
        contact_id=contact_id,
        starts_at=BookingStartsAtUnixSeconds(starts),
        ends_at=BookingEndsAtUnixSeconds(starts + length),
        party_size=model.party_size,
        status=BookingStatus.COMPLETED,
        source_channel=model.source_channel,
        language=model.language,
        service_item_id=model.service_item_id,
        buffer_minutes=model.buffer_minutes,
        value_minor=model.value_minor,
        currency_code=model.currency_code,
        created_at=made,
        updated_at=made,
    )


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
