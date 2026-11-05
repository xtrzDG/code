from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.notification_preferences import (
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.domain.staff_deliveries import StaffDeliveryStateDocument


class NotificationCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of staff notifications (migration 1043): the
    devices that receive them, each user's preferences and how delivery to
    each staff contact went. A sibling of DocumentCollectionsContainer with
    the same storage factory (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    push_subscription_collection = document_collection(
        PushSubscriptionDocument,
        "push_subscriptions",
        config,
        clients,
        utilities,
        time_provider,
    )
    notification_preferences_collection = document_collection(
        UserNotificationPreferencesDocument,
        "notification_preferences",
        config,
        clients,
        utilities,
        time_provider,
    )
    staff_delivery_state_collection = document_collection(
        StaffDeliveryStateDocument,
        "staff_delivery_states",
        config,
        clients,
        utilities,
        time_provider,
    )
