from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.notification_preferences import StaffNotificationPreferences
from app.schemas.domain.users import UserDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.constrained_integers import (
    BusinessRevision,
    RecordingRetentionDays,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import (
    BusinessName,
    CityName,
    RawManagerContactAddress,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.handoffs.constrained_strings import ManagerTelegramUsername
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.booleans import IsUserVerified
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import (
    RawEmailAddressInput,
    UserDisplayName,
)


class ManagerContactInput(ImmutableDTO):
    """
    Staff contact typed by the owner.

    The address is checked per channel: a numeric chat id for Telegram, a
    phone number of any country for WhatsApp and SMS (national formats use
    the business country), an e-mail address for e-mail. Without `language`
    the owner's language is used; without `preferences` every event arrives
    at any hour.
    """

    name: ManagerName
    channel: ManagerContactChannel
    address: RawManagerContactAddress
    language: LanguageTag | None = None
    preferences: StaffNotificationPreferences | None = None


class ManagerContactView(ImmutableDTO):
    """
    Validated staff contact that receives handoffs, bookings and leads:
    which events and quiet hours (None: all, any hour), and the Telegram
    @username of a chat linked through the platform bot.
    """

    name: ManagerName
    channel: ManagerContactChannel
    address: ManagerContactAddress
    language: LanguageTag
    preferences: StaffNotificationPreferences | None = None
    telegram_username: ManagerTelegramUsername | None = None


class BusinessMemberView(ImmutableDTO):
    """Team member with the details the owner needs to recognise them."""

    user_id: UserId
    role: BusinessMemberRole
    display_name: UserDisplayName | None = None
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    is_verified: IsUserVerified = False


class BusinessView(ImmutableDTO):
    """
    A business (tenant) as shown in the cabinet.

    `viewer_role` is the role of the user who asked; it is None for a
    platform admin who is not a member. `revision` grows with every save:
    send it back as `expected_revision` of a settings change.
    """

    id: BusinessId
    name: BusinessName
    niche_key: NicheKey
    country_code: CountryCode
    city: CityName | None = None
    timezone: TimezoneName
    currency_code: CurrencyCode
    languages: list[LanguageTag]
    default_language: LanguageTag
    owner_language: LanguageTag
    plan_key: PlanKey
    status: BusinessStatus
    service_mode: ServiceMode
    data_region: DataRegion
    recording_retention_days: RecordingRetentionDays
    members: list[BusinessMemberView]
    manager_contacts: list[ManagerContactView] = Field(
        default_factory=list[ManagerContactView]
    )
    published_assistant_version_id: AssistantVersionId | None = None
    viewer_role: BusinessMemberRole | None = None
    revision: BusinessRevision
    created_at: Microseconds


class BusinessViewSource(ImmutableDTO):
    """A business with the users behind its members, as seen by one viewer."""

    business: BusinessDocument
    member_users: list[UserDocument]
    viewer_id: UserId


class CreateBusinessRequest(ImmutableDTO):
    """
    HTTP body of business creation.

    Everything except name and niche is optional and filled from the
    country profile: country (the creator's phone country), time zone,
    customer languages, currency and data region. The default language
    must be one of the languages (the first one when missing); the owner
    language falls back to the creator's interface language; the plan to
    the niche's first recommended plan.
    """

    name: BusinessName
    niche_key: NicheKey
    country_code: CountryCode | None = None
    city: CityName | None = None
    timezone: TimezoneName | None = None
    languages: list[LanguageTag] | None = None
    default_language: LanguageTag | None = None
    owner_language: LanguageTag | None = None
    plan_key: PlanKey | None = None


class CreateBusinessCommand(ImmutableDTO):
    """Create a business owned by the signed-in user."""

    user_id: UserId
    details: CreateBusinessRequest


class BusinessQuery(ImmutableDTO):
    """Read one business on behalf of a signed-in user."""

    user_id: UserId
    business_id: BusinessId


class BusinessSettingsChanges(ImmutableDTO):
    """
    HTTP body of a settings change; missing fields stay unchanged.

    An empty `city` clears it. `manager_contacts` replaces the whole list.
    `status` only switches a live assistant to paused and back.

    `expected_revision` is the `revision` of the business the change was
    made from. When it is given and someone has saved the business since,
    nothing changes and the answer is 409 with the reason
    `stale_revision`: reload, then apply the change again. Without it the
    change applies to whatever is stored (scripts, older clients).
    """

    expected_revision: BusinessRevision | None = None
    name: BusinessName | None = None
    city: CityName | None = None
    timezone: TimezoneName | None = None
    languages: list[LanguageTag] | None = None
    default_language: LanguageTag | None = None
    owner_language: LanguageTag | None = None
    plan_key: PlanKey | None = None
    recording_retention_days: RecordingRetentionDays | None = None
    manager_contacts: list[ManagerContactInput] | None = None
    status: BusinessStatus | None = None


class UpdateBusinessSettingsCommand(ImmutableDTO):
    """Owner changes the settings of a business."""

    user_id: UserId
    business_id: BusinessId
    changes: BusinessSettingsChanges
    client_ip_address: ClientIpAddress | None = None


class InviteStaffRequest(ImmutableDTO):
    """
    HTTP body of a team invitation by phone number (any country) or e-mail.

    Exactly one of `phone_number` and `email` is set. National phone formats
    are read in `country_hint`, or in the business country when it is missing.
    `role` is staff unless an owner adds another owner, or an agency: an
    outside helper who does staff's work and builds the assistant, never
    billing, the team or copies of customers' data.

    Example: {"email": "chef@example.com", "role": "owner"}.
    """

    phone_number: RawPhoneNumberInput | None = None
    email: RawEmailAddressInput | None = None
    country_hint: CountryCode | None = None
    display_name: UserDisplayName | None = None
    role: BusinessMemberRole = BusinessMemberRole.STAFF


class InviteStaffCommand(ImmutableDTO):
    """Owner adds a staff member; unknown people get an unverified account."""

    user_id: UserId
    business_id: BusinessId
    invitation: InviteStaffRequest
    client_ip_address: ClientIpAddress | None = None


class MemberRoleChange(ImmutableDTO):
    """
    HTTP body of a role change of a team member.

    Example: {"role": "owner"}.
    """

    role: BusinessMemberRole


class ChangeMemberRoleCommand(ImmutableDTO):
    """Owner makes a member an owner or staff; the last owner stays owner."""

    user_id: UserId
    business_id: BusinessId
    member_user_id: UserId
    change: MemberRoleChange
    client_ip_address: ClientIpAddress | None = None


class RemoveMemberCommand(ImmutableDTO):
    """Owner removes a member; the last owner cannot be removed."""

    user_id: UserId
    business_id: BusinessId
    member_user_id: UserId
    client_ip_address: ClientIpAddress | None = None
