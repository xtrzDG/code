"""Bodies and inputs of the public API's creating operations."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.bookings import LeadType
from app.schemas.constants.integrations import BusinessEventType
from app.schemas.dto.public_api.access import PublicApiCall
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
    PartySize,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import (
    BookingNote,
    LeadBudgetText,
    LeadDetails,
)
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.integrations.constrained_strings import (
    WebhookEndpointLabel,
    WebhookTargetUrl,
)
from app.schemas.typings.integrations.prefixed_id import WebhookEndpointId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput


class PublicBookingRequest(ImmutableDTO):
    """
    A booking made through the API, as staff add one in the cabinet: the
    customer (a contact with the phone is reused, else a new one), the
    day and time in the business's time zone, a resource and a service.
    Capacity and opening hours are enforced.
    """

    contact_name: ContactName
    contact_phone_number: RawPhoneNumberInput | None = None
    resource_id: ResourceId | None = None
    service_id: KnowledgeItemId | None = None
    date: LocalDate
    time: LocalTimeOfDay | None = None
    duration_minutes: BookingDurationMinutes | None = None
    nights: NightCount | None = None
    party_size: PartySize
    notes: BookingNote | None = None
    language: LanguageTag | None = None


class PublicLeadRequest(ImmutableDTO):
    """A request the team should follow up (a contact form, a CRM)."""

    contact_name: ContactName
    contact_phone_number: RawPhoneNumberInput | None = None
    type: LeadType
    details: LeadDetails
    requested_date: LocalDate | None = None
    party_size: PartySize | None = None
    budget: LeadBudgetText | None = None
    language: LanguageTag | None = None


class PublicWebhookRequest(ImmutableDTO):
    """A REST-hook subscription (Zapier): where to POST which events."""

    url: WebhookTargetUrl
    event_types: list[BusinessEventType] = Field(min_length=1)
    label: WebhookEndpointLabel | None = None


class PublicBookingCommand(PublicApiCall):
    request: PublicBookingRequest


class PublicLeadCommand(PublicApiCall):
    request: PublicLeadRequest


class PublicWebhookCommand(PublicApiCall):
    request: PublicWebhookRequest


class PublicWebhookRemoval(PublicApiCall):
    endpoint_id: WebhookEndpointId
