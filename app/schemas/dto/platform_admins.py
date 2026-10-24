"""The platform admin team: roles, their rights, and the Team page."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.access import PlatformAdminPermission, PlatformAdminRole
from app.schemas.constants.users import LoginMethod
from app.schemas.typings.access.booleans import IsViewingAdmin
from app.schemas.typings.access.prefixed_id import PlatformAdminId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import RawEmailAddressInput, UserDisplayName


class PlatformAdminAccessRequest(ImmutableDTO):
    """Check that a signed-in person is a platform admin who may do this."""

    user_id: UserId
    permission: PlatformAdminPermission


class PlatformAdminView(ImmutableDTO):
    """
    One member of the admin team: how they sign in, their role, their name
    once they have signed in (`user_id` is None before), who added them
    (`added_by` None: bootstrapped from the PLATFORM_ADMIN_* lists; their
    name when they have one) and when. `is_you` marks the viewer.
    """

    id: PlatformAdminId
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    role: PlatformAdminRole
    user_id: UserId | None = None
    display_name: UserDisplayName | None = None
    added_by: UserId | None = None
    added_by_name: UserDisplayName | None = None
    created_at: Microseconds
    is_you: IsViewingAdmin = False


class PlatformAdminTeamView(ImmutableDTO):
    """The admin team, SUPER admins first, then by when they were added."""

    items: list[PlatformAdminView] = Field(default_factory=list[PlatformAdminView])


class AddPlatformAdminRequest(ImmutableDTO):
    """
    Add a person to the admin team by the phone number (international
    format) or e-mail they sign in with; exactly one is set.
    """

    phone_number: RawPhoneNumberInput | None = None
    email: RawEmailAddressInput | None = None
    role: PlatformAdminRole


class AddPlatformAdminCommand(ImmutableDTO):
    user_id: UserId
    phone_number: RawPhoneNumberInput | None = None
    email: RawEmailAddressInput | None = None
    role: PlatformAdminRole
    client_ip_address: ClientIpAddress | None = None


class ChangePlatformAdminRoleRequest(ImmutableDTO):
    """Give a member of the admin team another role."""

    role: PlatformAdminRole


class ChangePlatformAdminRoleCommand(ImmutableDTO):
    user_id: UserId
    admin_id: PlatformAdminId
    role: PlatformAdminRole
    client_ip_address: ClientIpAddress | None = None


class RemovePlatformAdminCommand(ImmutableDTO):
    """Take someone off the admin team; their rights end at once."""

    user_id: UserId
    admin_id: PlatformAdminId
    client_ip_address: ClientIpAddress | None = None


class PlatformAdminTeamQuery(ImmutableDTO):
    user_id: UserId
