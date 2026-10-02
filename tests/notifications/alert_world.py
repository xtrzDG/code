"""A business, its contacts and devices, and the alert facilitator over fakes."""

from datetime import datetime

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.push_subscriptions import (
    PushSubscriptionDocument,
    PushSubscriptionKeys,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.notifications.constrained_strings import (
    PushAuthSecret,
    PushEndpointUrl,
    PushPublicKey,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.staff_delivery_keys import push_subscription_id
from tests.notifications.staff_alert_fakes import (
    RecordingPushQueue,
    build_staff_alerts,
    preferences_repo,
    push_subscription_repo,
    settings_without_cabinet,
)
from tests.notifications.test_web_push_encryption import AUTH_SECRET, RECEIVER_PUBLIC
from tests.operations.builders import manager
from tests.operations.fakes import (
    FakeLocalizedTextResolver,
    MovableClock,
    RecordingManagerNotifier,
)

CABINET: str = "https://cabinet.example.com"
# Monday 2026-10-05 12:00 in Tbilisi.
NOON: datetime = datetime.fromisoformat("2026-10-05T12:00:00+04:00")


def build_business(owner: UserId, staff: UserId) -> BusinessDocument:
    return BusinessDocument(
        name=BusinessName("Salobie Bia"),
        niche_key=NicheKey.RESTAURANT,
        country_code=CountryCode("GE"),
        timezone=TimezoneName("Asia/Tbilisi"),
        currency_code=CurrencyCode("GEL"),
        languages=[LanguageTag("ka"), LanguageTag("en")],
        default_language=LanguageTag("ka"),
        owner_language=LanguageTag("ka"),
        plan_key=PlanKey.VOICE_AND_CHAT,
        data_region=DataRegion.EU,
        members=[
            BusinessMember(user_id=owner, role=BusinessMemberRole.OWNER),
            BusinessMember(user_id=staff, role=BusinessMemberRole.STAFF),
        ],
        manager_contacts=[
            manager("Nino", ManagerContactChannel.TELEGRAM, "4242", "ka"),
            manager("Anna", ManagerContactChannel.EMAIL, "anna@example.com", "en"),
            manager("Gio", ManagerContactChannel.SMS, "+995555000222", "ru"),
        ],
    )


class AlertWorld:
    """The real staff alert facilitator with recording edges."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.clock = MovableClock(NOON)
        self.owner, self.staff = UserId(), UserId()
        self.business = build_business(self.owner, self.staff)
        self.notifier = RecordingManagerNotifier()
        self.push_queue = RecordingPushQueue()
        self.subscriptions = push_subscription_repo()
        self.preferences = preferences_repo()
        self.settings = settings or settings_without_cabinet().model_copy(
            update={"cabinet_base_url": CABINET}
        )
        self.alerts = build_staff_alerts(
            self.notifier,
            FakeLocalizedTextResolver(),
            self.clock.wall_clock,
            settings=self.settings,
            push_queue=self.push_queue,
            subscriptions=self.subscriptions,
            preferences=self.preferences,
        )

    def add_device(self, user: UserId, language: str) -> PushSubscriptionDocument:
        endpoint = f"https://fcm.googleapis.com/fcm/send/{user}-{language}"
        device = PushSubscriptionDocument(
            id=push_subscription_id(self.business.id, user, endpoint),
            business_id=self.business.id,
            user_id=user,
            endpoint=PushEndpointUrl(endpoint),
            keys=PushSubscriptionKeys(
                p256dh=PushPublicKey(RECEIVER_PUBLIC), auth=PushAuthSecret(AUTH_SECRET)
            ),
            language=LanguageTag(language),
        )
        self.subscriptions.save(device)
        return device
