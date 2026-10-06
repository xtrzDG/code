"""A resource's busy times fetched as an iCal feed by a calendar (public)."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_strings import IcalExportTokenHash
from app.schemas.typings.calendar_sync.strings import IcalExportToken, IcalFeedText
from app.schemas.typings.compliance.strings import ClientIpAddress


class IcalExportRequest(ImmutableDTO):
    """The token of an export address, and who fetches it (rate limits)."""

    token: IcalExportToken
    client_ip_address: ClientIpAddress | None = None


class IcalExportClaims(ImmutableDTO):
    """The resource an export address belongs to, once its token checked out."""

    business_id: BusinessId
    resource_id: ResourceId
    token_hash: IcalExportTokenHash


class IcalExportFile(ImmutableDTO):
    """The feed: one VCALENDAR (RFC 5545) with CRLF lines."""

    content: IcalFeedText
