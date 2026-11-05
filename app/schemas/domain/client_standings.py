from base_pydantic_schemas import BaseDocument, SchemaVersion

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.client_health import ClientHealthStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.client_health.booleans import IsClientLosingMoney
from app.schemas.typings.client_health.constrained_integers import (
    ClientListPosition,
)
from app.schemas.typings.client_health.strings import ClientSummarySnapshot
from app.schemas.typings.localization.constrained_strings import CountryCode


class ClientStandingDocument(BaseDocument):
    """
    One client as the platform admin's client list shows it (a platform
    collection, migration 1122; the storage key is the business id).

    The `refresh_client_standings` periodic job writes it from the
    client's summary every few minutes: the summary of that moment, the
    fields the list filters and counts by, and the client's position in
    each order of the list among every client (0 first; ties keep health,
    then name order, as the summaries sort). The list then reads one keyset
    page and database counts instead of summarizing every client on each
    request; the client's own page stays live. `updated_at` is when the
    summary was taken.
    """

    schema_version: SchemaVersion = SchemaVersion("1")
    business_id: BusinessId
    name: BusinessName
    business_status: BusinessStatus
    health_status: ClientHealthStatus
    country_code: CountryCode
    niche_key: NicheKey
    is_losing_money: IsClientLosingMoney = False
    summary: ClientSummarySnapshot
    health_position: ClientListPosition
    name_position: ClientListPosition
    usage_position: ClientListPosition
    margin_position: ClientListPosition
    cost_position: ClientListPosition
    revenue_position: ClientListPosition
