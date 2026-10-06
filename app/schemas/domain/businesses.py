from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.notification_preferences import StaffNotificationPreferences
from app.schemas.domain.referrals import BusinessReferral
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.constrained_integers import (
    BusinessRevision,
    RecordingRetentionDays,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName, CityName
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.handoffs.constrained_strings import ManagerTelegramUsername
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.mfa.booleans import IsMfaRequiredForMembers
from app.schemas.typings.referrals.booleans import IsPoweredByHidden
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug
from app.schemas.typings.users.prefixed_id import UserId


class BusinessMember(PersistentDocument):
    """A user with a role inside one business."""

    user_id: UserId
    role: BusinessMemberRole


class ManagerContact(PersistentDocument):
    """
    Staff contact that receives handoffs, bookings and leads, in their
    language. `preferences` (None: every event, at any hour) choose which
    events reach them and their quiet hours; `telegram_username` is the
    @username of a chat linked through the platform bot, shown instead of
    the chat id.
    """

    name: ManagerName
    channel: ManagerContactChannel
    address: ManagerContactAddress
    language: LanguageTag
    preferences: StaffNotificationPreferences | None = None
    telegram_username: ManagerTelegramUsername | None = None


class BusinessDocument(BaseDocument):
    """
    A business (tenant) with one AI assistant (concept table `tenants`).

    Country-dependent values (time zone, currency, languages, data region) are
    filled from the country profile at creation and may be changed by the owner.
    `default_language` is the greeting language and must be one of `languages`.
    `revision` grows with every save (the repository sets it): settings
    changes made from an older revision are refused (optimistic concurrency).

    Version 2: manager contacts may carry notification preferences and a
    Telegram username (both optional, so version 1 rows read as they are).
    Version 3: `public_slug`, the address of the hosted chat page
    (`/c/{slug}`; None until the owner first shares the assistant, so older
    rows read as they are). Its uniqueness is kept by the slug claims.
    Version 4: `require_mfa_for_members` (False by default, so older rows
    read as they are): the team opens the business only with sessions
    signed in with two factors.
    Version 5: `dpa_version_accepted`, the data processing agreement version
    an owner accepted last (None until the first acceptance; businesses that
    accepted before version 5 are answered by their acceptance records).
    Version 6: `referred_by`, the code its owner signed up by (None: nobody
    referred it, as for every older row), and `hides_powered_by`, the Plus
    owner's choice to leave the "Powered by" link off the chat and the
    table card (False, so older rows read as they are).
    """

    schema_version: SchemaVersion = SchemaVersion("6")
    id: BusinessId = Field(default_factory=BusinessId)
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
    status: BusinessStatus = BusinessStatus.ONBOARDING
    service_mode: ServiceMode = ServiceMode.FULL
    data_region: DataRegion
    members: list[BusinessMember]
    manager_contacts: list[ManagerContact] = Field(default_factory=list[ManagerContact])
    recording_retention_days: RecordingRetentionDays = RecordingRetentionDays(90)
    published_assistant_version_id: AssistantVersionId | None = None
    public_slug: BusinessPublicSlug | None = None
    require_mfa_for_members: IsMfaRequiredForMembers = False
    dpa_version_accepted: DpaDocumentVersion | None = None
    referred_by: BusinessReferral | None = None
    hides_powered_by: IsPoweredByHidden = False
    revision: BusinessRevision = BusinessRevision(0)
