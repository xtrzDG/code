"""The websites allowed to show a business's chat, and the check of a request."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.spend.booleans import IsWidgetOriginRestricted
from app.schemas.typings.spend.constrained_strings import (
    WidgetPageOrigin,
    WidgetSiteAddress,
)
from app.schemas.typings.users.prefixed_id import UserId


class WidgetOriginCheck(ImmutableDTO):
    """A website-chat request of a business, from the page it came from."""

    business_id: BusinessId
    page_origin: WidgetPageOrigin | None = None


class WidgetAllowedOriginsQuery(ImmutableDTO):
    """A team member asks which websites may show the business's chat."""

    user_id: UserId
    business_id: BusinessId


class WidgetAllowedOriginsRequest(ImmutableDTO):
    """
    The websites, as the owner types them (at most 20; an empty list lets
    any website show the chat again).
    """

    origins: list[WidgetSiteAddress] = Field(
        default_factory=list[WidgetSiteAddress], max_length=20
    )


class SaveWidgetAllowedOriginsCommand(ImmutableDTO):
    """The owner saves the websites allowed to show the chat."""

    user_id: UserId
    business_id: BusinessId
    request: WidgetAllowedOriginsRequest


class WidgetAllowedOriginsView(ImmutableDTO):
    """
    The websites allowed to show the chat (origins, in the owner's order),
    whether the list restricts it at all, and the platform's own pages that
    always may (the hosted chat page and the cabinet's preview).
    """

    origins: list[PublicBaseUrl]
    is_restricted: IsWidgetOriginRestricted
    always_allowed: list[PublicBaseUrl]
