"""
What a new location takes from the location it is made from: the profile,
resources, knowledge and channel settings. Never channel tokens or
accounts, payment settings, API keys, webhooks or anyone's personal data.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import WebChatAppearance, WhatsAppStaffTemplate
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId


class ChannelSettingsTemplate(ImmutableDTO):
    """
    A channel's own settings, without its account: how the website chat
    looks, which WhatsApp templates staff replies use. The new location
    connects its own accounts.
    """

    kind: ChannelKind
    web_chat_appearance: WebChatAppearance | None = None
    whatsapp_staff_template: WhatsAppStaffTemplate | None = None
    whatsapp_staff_templates: list[WhatsAppStaffTemplate] = Field(
        default_factory=list[WhatsAppStaffTemplate]
    )


class LocationTemplate(ImmutableDTO):
    """The parts of a location a new one starts from (read in its scope)."""

    profile: BusinessProfileDocument | None = None
    resources: list[ResourceDocument] = Field(default_factory=list[ResourceDocument])
    knowledge_items: list[KnowledgeItemDocument] = Field(
        default_factory=list[KnowledgeItemDocument]
    )
    channels: list[ChannelSettingsTemplate] = Field(
        default_factory=list[ChannelSettingsTemplate]
    )


class LocationTemplateQuery(ImmutableDTO):
    """Read a location's template, for an owner of it (a brand owner)."""

    user_id: UserId
    business_id: BusinessId


class LocationTemplateWrite(ImmutableDTO):
    """Fill a new location from a template, for its owner."""

    user_id: UserId
    business_id: BusinessId
    template: LocationTemplate


class ClonedLocationRequest(ImmutableDTO):
    """
    The new business itself: the source's settings (niche, country, time
    zone, languages, plan), the new name and city, the brand, and the
    brand owner who asked as its owner.
    """

    user_id: UserId
    brand_id: BrandId
    source: BusinessDocument
    name: BusinessName
    city: CityName | None = None
    client_ip_address: ClientIpAddress | None = None
