"""Fakes and builders of the staff alert path, shared by the test packages."""

import threading
from collections.abc import Mapping

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.notifications import PushNotificationQueueContract
from app.facilitators.notifications.staff_alert_facilitator import (
    StaffAlertFacilitator,
)
from app.repositories.notification_repositories import (
    NotificationPreferencesRepository,
    PushSubscriptionRepository,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.notification_preferences import (
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.dto.notifications.staff_alerts import PushNotification
from app.schemas.typings.platform.strings import PlatformSecret
from app.transformers.notifications.staff_notification_text_transformer import (
    StaffNotificationTextTransformer,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.notifications.staff_link_signer import StaffLinkSigner

TEST_ENCRYPTION_KEY: PlatformSecret = PlatformSecret(
    "test-encryption-key-for-notification-links"
)


class RecordingPushQueue(PushNotificationQueueContract):
    """Records device notifications; subscriptions listed as failing get False."""

    def __init__(self, failing: frozenset[str] = frozenset()) -> None:
        self._failing: frozenset[str] = failing
        self._lock: threading.Lock = threading.Lock()
        self.queued: list[PushNotification] = []

    def queue(self, notification: PushNotification) -> bool:
        with self._lock:
            self.queued.append(notification)

        return str(notification.subscription_id) not in self._failing


def settings_without_cabinet(
    environment: Mapping[str, str] | None = None,
) -> AppSettings:
    """Production-like settings without CABINET_BASE_URL: no link lines."""

    settings: AppSettings = assemble_app_settings(dict(environment or {}))
    return settings.model_copy(update={"cabinet_base_url": None})


def push_subscription_repo() -> PushSubscriptionRepository:
    return PushSubscriptionRepository(
        InMemoryDocumentCollectionAdapter[PushSubscriptionDocument](
            PushSubscriptionDocument
        )
    )


def preferences_repo() -> NotificationPreferencesRepository:
    return NotificationPreferencesRepository(
        InMemoryDocumentCollectionAdapter[UserNotificationPreferencesDocument](
            UserNotificationPreferencesDocument
        )
    )


def build_staff_alerts(
    notifier: ManagerNotificationFacilitatorContract,
    resolver: LocalizedTextResolverContract,
    wall_clock: WallClock[Microseconds],
    settings: AppSettings | None = None,
    push_queue: PushNotificationQueueContract | None = None,
    subscriptions: PushSubscriptionRepository | None = None,
    preferences: NotificationPreferencesRepository | None = None,
) -> StaffAlertFacilitator:
    """The real alert facilitator over fakes (no links unless settings say)."""

    return StaffAlertFacilitator(
        manager_notifier=notifier,
        push_queue=push_queue or RecordingPushQueue(),
        push_subscription_repo=subscriptions or push_subscription_repo(),
        notification_preferences_repo=preferences or preferences_repo(),
        link_signer=StaffLinkSigner(TEST_ENCRYPTION_KEY),
        text_transformer=StaffNotificationTextTransformer(resolver),
        app_settings=settings or settings_without_cabinet(),
        wall_clock=wall_clock,
    )
