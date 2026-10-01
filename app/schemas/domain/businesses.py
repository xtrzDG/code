from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.accounts.prefixed_id import OwnerId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.booleans import IsChannelEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessAddress, BusinessName
from app.schemas.typings.channels.strings import ChannelAccountId, ChannelSecret
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)


class ChannelConnection(PersistentDocument):
    """One customer channel connected to a business assistant."""

    kind: ChannelKind
    is_enabled: IsChannelEnabled = True
    account_id: ChannelAccountId | None = None
    secret: ChannelSecret | None = None


class ManagerContact(PersistentDocument):
    """Staff member who receives handoffs and leads, in their own language."""

    name: ManagerName
    channel: ManagerContactChannel
    address: ManagerContactAddress
    language: LanguageTag


class BusinessDocument(BaseDocument):
    """
    A business (tenant) with one AI assistant.

    Country-dependent values (time zone, currency, languages, data region) are
    filled from the country profile at creation and may be changed by the owner.
    """

    id: BusinessId = Field(default_factory=BusinessId)
    owner_id: OwnerId
    name: BusinessName
    niche_key: NicheKey
    country_code: CountryCode
    timezone: TimezoneName
    currency_code: CurrencyCode
    owner_language: LanguageTag
    customer_languages: list[LanguageTag]
    plan_key: PlanKey
    status: BusinessStatus = BusinessStatus.DRAFT
    data_region: DataRegion
    venue_phone_number: E164PhoneNumber | None = None
    assistant_phone_number: E164PhoneNumber | None = None
    address: BusinessAddress | None = None
    channels: list[ChannelConnection] = Field(default_factory=list[ChannelConnection])
    manager_contacts: list[ManagerContact] = Field(default_factory=list[ManagerContact])
    active_assistant_version_id: AssistantVersionId | None = None
