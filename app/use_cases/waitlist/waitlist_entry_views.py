"""The cabinet's view of waitlist entries and of the waitlist's settings."""

from collections.abc import Mapping
from datetime import datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.domain.waitlist import (
    WaitlistEntryDocument,
    WaitlistOffer,
    WaitlistSettingsDocument,
)
from app.schemas.dto.growth.growth_counts import WaitlistStatusCount
from app.schemas.dto.growth.waitlist_views import (
    WaitlistEntryView,
    WaitlistOfferView,
    WaitlistSettingsView,
)
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.utilities.scheduling.zoned_time import to_local_date, to_local_moment
from app.utilities.waitlist.waitlist_keys import waitlist_settings_id_of


def build_entry_view(
    entry: WaitlistEntryDocument,
    contacts: Mapping[ContactId, ContactDocument],
    resources: Mapping[ResourceId, ResourceDocument],
    items: Mapping[KnowledgeItemId, KnowledgeItemDocument],
    zone: ZoneInfo,
) -> WaitlistEntryView:
    contact: ContactDocument | None = contacts.get(entry.contact_id)
    resource = None if entry.resource_id is None else resources.get(entry.resource_id)
    item = None if entry.service_item_id is None else items.get(entry.service_item_id)
    return WaitlistEntryView(
        id=entry.id,
        contact_id=entry.contact_id,
        contact_name=customer_name(entry, contact),
        conversation_id=entry.conversation_id,
        source_channel=entry.source_channel,
        language=entry.language,
        date=entry.date,
        time_from=entry.time_from,
        time_to=entry.time_to,
        party_size=entry.party_size,
        nights=entry.nights,
        resource_kind=entry.resource_kind,
        resource_id=entry.resource_id,
        resource_name=None if resource is None else resource.name,
        service_item_id=entry.service_item_id,
        service_title=None if item is None else item.title,
        notes=entry.notes,
        status=entry.status,
        end_reason=entry.end_reason,
        offer=(
            None
            if entry.offer is None
            else build_offer_view(entry, entry.offer, resources, zone)
        ),
        offer_count=entry.offer_count,
        booking_id=entry.booking_id,
        booked_at=entry.booked_at,
        created_at=entry.created_at,
        ended_at=entry.ended_at,
    )


def customer_name(
    entry: WaitlistEntryDocument, contact: ContactDocument | None
) -> ContactName | None:
    """The name the wish was made under, else the contact's (none once erased)."""

    if contact is not None and contact.erased_at is not None:
        return None

    return entry.contact_name or (None if contact is None else contact.name)


def build_offer_view(
    entry: WaitlistEntryDocument,
    offer: WaitlistOffer,
    resources: Mapping[ResourceId, ResourceDocument],
    zone: ZoneInfo,
) -> WaitlistOfferView:
    starts: datetime = to_local_moment(int(offer.starts_at), zone)
    ends: datetime = to_local_moment(int(offer.ends_at), zone)
    resource: ResourceDocument | None = resources.get(offer.resource_id)
    return WaitlistOfferView(
        resource_id=offer.resource_id,
        resource_name=None if resource is None else resource.name,
        date=to_local_date(starts.date()),
        time=LocalTimeOfDay(starts.strftime("%H:%M")),
        end_time=LocalTimeOfDay(ends.strftime("%H:%M")),
        offered_at=offer.offered_at,
        expires_at=entry.offer_expires_at,
        channel=offer.channel,
        freed_booking_id=offer.freed_booking_id,
    )


def stored_or_default(
    settings: WaitlistSettingsDocument | None,
    business_id: BusinessId,
    created_at: Microseconds,
) -> WaitlistSettingsDocument:
    """The stored settings, else the defaults (on, a 30-minute hold)."""

    if settings is not None:
        return settings

    return WaitlistSettingsDocument(
        id=waitlist_settings_id_of(business_id),
        business_id=business_id,
        created_at=created_at,
        updated_at=created_at,
    )


def build_settings_view(
    settings: WaitlistSettingsDocument, counts: list[WaitlistStatusCount]
) -> WaitlistSettingsView:
    return WaitlistSettingsView(
        is_enabled=settings.is_enabled,
        hold_minutes=settings.hold_minutes,
        counts=counts,
    )
