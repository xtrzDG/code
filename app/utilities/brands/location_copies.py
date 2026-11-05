"""
A new location's own copies of another location's profile, resources,
knowledge and channel settings: new ids, the links between resources and
knowledge items mapped onto the copies, and nothing that names an outside
account (calendar links, channel accounts and tokens), a conversation (an
owner's answer correction) or the other location's place and people (its
address, review page and phone numbers, the handoff number included).
"""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessContacts, BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.brands.location_templates import (
    ChannelSettingsTemplate,
    LocationTemplate,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId


@dataclass(frozen=True)
class LocationCopies:
    """Everything the new location stores, ready to save."""

    profile: BusinessProfileDocument | None
    resources: list[ResourceDocument] = field(default_factory=list[ResourceDocument])
    knowledge_items: list[KnowledgeItemDocument] = field(
        default_factory=list[KnowledgeItemDocument]
    )
    channels: list[ChannelDocument] = field(default_factory=list[ChannelDocument])


def copy_location(
    template: LocationTemplate,
    business_id: BusinessId,
    now: Microseconds,
) -> LocationCopies:
    resource_ids: dict[ResourceId, ResourceId] = {
        resource.id: ResourceId() for resource in template.resources
    }
    item_ids: dict[KnowledgeItemId, KnowledgeItemId] = {
        item.id: KnowledgeItemId() for item in template.knowledge_items
    }
    profile: BusinessProfileDocument | None = (
        None
        if template.profile is None
        else template.profile.model_copy(
            update={
                "business_id": business_id,
                # Where this location is, its review page and the numbers
                # customers and handoffs reach are its own.
                "address": None,
                "google_review_url": None,
                "contacts": BusinessContacts(),
                "created_at": now,
                "updated_at": now,
            },
            deep=True,
        )
    )
    resources: list[ResourceDocument] = [
        resource.model_copy(
            update={
                "id": resource_ids[resource.id],
                "business_id": business_id,
                "serves_item_ids": [
                    item_ids[item_id]
                    for item_id in resource.serves_item_ids
                    if item_id in item_ids
                ],
                "room_type_item_id": item_ids.get(resource.room_type_item_id)
                if resource.room_type_item_id is not None
                else None,
                "external_calendar_id": None,
                "created_at": now,
                "updated_at": now,
            },
            deep=True,
        )
        for resource in template.resources
    ]
    items: list[KnowledgeItemDocument] = [
        item.model_copy(
            update={
                "id": item_ids[item.id],
                "business_id": business_id,
                "performer_resource_ids": [
                    resource_ids[resource_id]
                    for resource_id in item.performer_resource_ids
                    if resource_id in resource_ids
                ],
                "correction_of": None,
                "created_at": now,
                "updated_at": now,
            },
            deep=True,
        )
        for item in template.knowledge_items
    ]
    return LocationCopies(
        profile=profile,
        resources=resources,
        knowledge_items=items,
        channels=[
            copy_channel_settings(settings, business_id, now)
            for settings in template.channels
        ],
    )


def copy_channel_settings(
    settings: ChannelSettingsTemplate,
    business_id: BusinessId,
    now: Microseconds,
) -> ChannelDocument:
    """A channel waiting for the new location's own account (PENDING)."""

    return ChannelDocument(
        business_id=business_id,
        kind=settings.kind,
        status=ChannelStatus.PENDING,
        web_chat_appearance=settings.web_chat_appearance,
        whatsapp_staff_template=settings.whatsapp_staff_template,
        whatsapp_staff_templates=list(settings.whatsapp_staff_templates),
        created_at=now,
        updated_at=now,
    )
