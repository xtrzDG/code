"""
Platform support's access to a client's cabinet: the check of each
request, the owner's view and consent, and the admin's own grant.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.access import BusinessAccessMode, SupportAccessEndReason
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.typings.access.booleans import (
    IsOwnSupportAccess,
    IsSupportChangeAllowed,
    IsSupportViewer,
    IsSupportWriteAllowed,
)
from app.schemas.typings.access.constrained_integers import SupportWriteAccessHours
from app.schemas.typings.access.constrained_strings import SupportAccessReason
from app.schemas.typings.access.prefixed_id import SupportAccessGrantId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName


class SupportAccessCheck(ImmutableDTO):
    """
    May this person, who is not a member, act on the business as platform
    support right now? `access_mode` None takes the request's own (from
    the HTTP method), or READ for background work.
    """

    user_id: UserId
    business_id: BusinessId
    required_role: BusinessMemberRole | None = None
    access_mode: BusinessAccessMode | None = None
    support_may_change: IsSupportChangeAllowed = False


class SupportAccessEnding(ImmutableDTO):
    """When, by whom (None: by time) and why a support grant ends."""

    ended_at: Microseconds
    ended_by: UserId | None = None
    reason: SupportAccessEndReason


class SupportSessionView(ImmutableDTO):
    """
    One platform admin's open look into the cabinet: who (their name, or
    None: shown as "Platform support"), why, since and until when.
    `is_yours` marks the viewer's own.
    """

    grant_id: SupportAccessGrantId
    admin_name: UserDisplayName | None = None
    reason: SupportAccessReason
    started_at: Microseconds
    expires_at: Microseconds
    is_yours: IsOwnSupportAccess = False


class SupportWriteAccessView(ImmutableDTO):
    """
    Whether the owner lets support change things, and until when (None
    while it is off).
    """

    is_allowed: IsSupportWriteAllowed = False
    expires_at: Microseconds | None = None


class SupportAccessView(ImmutableDTO):
    """
    Platform support in this business now: the open looks into the cabinet,
    the owner's consent to changes, and the viewer's own position (a
    support admin, and whether they may change things right now).
    """

    sessions: list[SupportSessionView] = Field(default_factory=list[SupportSessionView])
    write_access: SupportWriteAccessView = Field(default_factory=SupportWriteAccessView)
    is_support_viewer: IsSupportViewer = False
    viewer_can_write: IsSupportWriteAllowed = False


class SupportAccessQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class UpdateSupportWriteAccessRequest(ImmutableDTO):
    """
    The owner turns support's permission to change things on (for `hours`,
    a day by default) or off.
    """

    is_allowed: IsSupportWriteAllowed
    hours: SupportWriteAccessHours | None = None


class UpdateSupportWriteAccessCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    is_allowed: IsSupportWriteAllowed
    hours: SupportWriteAccessHours | None = None
    client_ip_address: ClientIpAddress | None = None


class EndSupportAccessCommand(ImmutableDTO):
    """The owner ends every open support look into the cabinet."""

    user_id: UserId
    business_id: BusinessId
    client_ip_address: ClientIpAddress | None = None


class OpenClientCabinetRequest(ImmutableDTO):
    """Why a platform admin opens the client's cabinet (the owner sees it)."""

    reason: SupportAccessReason


class CloseClientCabinetCommand(ImmutableDTO):
    """A platform admin ends their own look into a client's cabinet."""

    user_id: UserId
    business_id: BusinessId
    client_ip_address: ClientIpAddress | None = None
