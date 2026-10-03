from app.contracts.repositories.notification_repositories import (
    NotificationPreferencesRepoContract,
    PushSubscriptionChange,
    PushSubscriptionRepoContract,
    StaffDeliveryStateChange,
    StaffDeliveryStateRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals
from app.schemas.domain.notification_preferences import (
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.domain.staff_deliveries import StaffDeliveryStateDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.notifications.prefixed_id import (
    PushSubscriptionId,
    StaffDeliveryStateId,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.notifications.staff_delivery_keys import preferences_id_of

USER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("user_id")


class PushSubscriptionRepository(
    BusinessScopedRepository[PushSubscriptionDocument],
    PushSubscriptionRepoContract,
):
    """The devices of a business's users, by business and by user (indexed)."""

    def save(self, subscription: PushSubscriptionDocument) -> None:
        self._store(str(subscription.id), subscription)

    def get(
        self,
        business_id: BusinessId,
        subscription_id: PushSubscriptionId,
    ) -> PushSubscriptionDocument | None:
        return self._load(business_id, str(subscription_id))

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[PushSubscriptionDocument]:
        return self._list_in_business(business_id)

    def list_by_user(
        self,
        business_id: BusinessId,
        user_id: UserId,
    ) -> list[PushSubscriptionDocument]:
        return self._list_in_business(
            business_id, (field_equals(USER_ID_FIELD, user_id),)
        )

    def update(
        self,
        business_id: BusinessId,
        subscription_id: PushSubscriptionId,
        change: PushSubscriptionChange,
    ) -> PushSubscriptionDocument | None:
        return self._modify_in_business(business_id, str(subscription_id), change)

    def delete(
        self, business_id: BusinessId, subscription_id: PushSubscriptionId
    ) -> None:
        self._remove(business_id, str(subscription_id))


class NotificationPreferencesRepository(
    BusinessScopedRepository[UserNotificationPreferencesDocument],
    NotificationPreferencesRepoContract,
):
    """One user's preferences in one business, keyed by the derived id."""

    def get(
        self,
        business_id: BusinessId,
        user_id: UserId,
    ) -> UserNotificationPreferencesDocument | None:
        return self._load(business_id, str(preferences_id_of(business_id, user_id)))

    def save(self, preferences: UserNotificationPreferencesDocument) -> None:
        self._store(str(preferences.id), preferences)


class StaffDeliveryStateRepository(
    BusinessScopedRepository[StaffDeliveryStateDocument],
    StaffDeliveryStateRepoContract,
):
    """How delivery to each staff contact went, by business (indexed)."""

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[StaffDeliveryStateDocument]:
        return self._list_in_business(business_id)

    def record(
        self,
        business_id: BusinessId,
        state_id: StaffDeliveryStateId,
        change: StaffDeliveryStateChange,
    ) -> StaffDeliveryStateDocument | None:
        key: str = str(state_id)
        updated: StaffDeliveryStateDocument | None = self._modify_in_business(
            business_id, key, change
        )
        if updated is not None or self._load(business_id, key) is not None:
            return updated

        created: StaffDeliveryStateDocument | None = change(None)
        if created is None:
            return None

        if self._collection.insert_if_absent(key, created):
            return created

        # Another writer stored the first state meanwhile: change that one.
        return self._modify_in_business(business_id, key, change)
