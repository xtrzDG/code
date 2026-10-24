"""A brand's other location the assistant may offer when its own is full."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.bookings.constrained_strings import (
    LocalDate,
    LocalTimeOfDay,
)
from app.schemas.typings.brands.booleans import IsSisterStayFree
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.strings import (
    AddressText,
    BusinessName,
    CityName,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    TimezoneName,
)
from app.schemas.typings.sharing.constrained_strings import HostedChatUrl


class SisterLocationOption(ImmutableDTO):
    """
    A location of the same brand that is free on the asked date: up to a
    few of its nearest free times there (in its own time zone), or a free
    stay of the asked nights, and how the customer reaches it (its address,
    phone and chat page). The assistant offers it; it cannot book there.
    """

    name: BusinessName
    city: CityName | None = None
    address: AddressText | None = None
    maps_url: WebLink | None = None
    phone_number: E164PhoneNumber | None = None
    chat_url: HostedChatUrl | None = None
    timezone: TimezoneName
    date: LocalDate
    free_times: list[LocalTimeOfDay] = Field(default_factory=list[LocalTimeOfDay])
    has_free_stay: IsSisterStayFree = False
