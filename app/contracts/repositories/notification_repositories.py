"""
Persistence contracts of staff notifications: the devices of cabinet users
(Web Push), each user's preferences, and how delivery to each staff
contact went. Every read is limited to one business.
"""

from collections.abc import Callable
from typing import Protocol

from app.contracts.repo_contract import RepoContract
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
from app.schemas.typings.users.prefixed_id import UserId

type PushSubscriptionChange = Callable[
    [PushSubscriptionDocument], PushSubscriptionDocument | None
]
type StaffDeliveryStateChange = Callable[
    [StaffDeliveryStateDocument | None], StaffDeliveryStateDocument | None
]


class PushSubscriptionRepoContract(RepoContract, Protocol):
    def save(self, subscription: PushSubscriptionDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        subscription_id: PushSubscriptionId,
    ) -> PushSubscriptionDocument | None:
        raise NotImplementedError

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[PushSubscriptionDocument]:
        raise NotImplementedError

    def list_by_user(
        self,
        business_id: BusinessId,
        user_id: UserId,
    ) -> list[PushSubscriptionDocument]:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        subscription_id: PushSubscriptionId,
        change: PushSubscriptionChange,
    ) -> PushSubscriptionDocument | None:
        """
        Store what `change` makes of the subscription as stored now; None,
        and nothing written, when it is gone or `change` returns None.
        """
        raise NotImplementedError

    def delete(
        self, business_id: BusinessId, subscription_id: PushSubscriptionId
    ) -> None:
        raise NotImplementedError


class NotificationPreferencesRepoContract(RepoContract, Protocol):
    def get(
        self,
        business_id: BusinessId,
        user_id: UserId,
    ) -> UserNotificationPreferencesDocument | None:
        raise NotImplementedError

    def save(self, preferences: UserNotificationPreferencesDocument) -> None:
        raise NotImplementedError


class StaffDeliveryStateRepoContract(RepoContract, Protocol):
    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[StaffDeliveryStateDocument]:
        raise NotImplementedError

    def record(
        self,
        business_id: BusinessId,
        state_id: StaffDeliveryStateId,
        change: StaffDeliveryStateChange,
    ) -> StaffDeliveryStateDocument | None:
        """
        Store what `change` makes of the state as stored now (None: no state
        yet), in one step; nothing is written when `change` returns None.
        """
        raise NotImplementedError
