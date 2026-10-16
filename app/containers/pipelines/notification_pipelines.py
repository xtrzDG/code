from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.notification_orchestrators import (
    NotificationOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class NotificationPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of Settings → Notifications."""

    notifications: NotificationOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    list_notification_contacts_pipeline = orchestrator_pipeline(
        notifications.list_notification_contacts_orchestrator
    )
    check_contact_pipeline = orchestrator_pipeline(
        notifications.check_contact_orchestrator
    )
    get_notification_settings_pipeline = orchestrator_pipeline(
        notifications.get_notification_settings_orchestrator
    )
    update_notification_preferences_pipeline = orchestrator_pipeline(
        notifications.update_notification_preferences_orchestrator
    )
    subscribe_push_pipeline = orchestrator_pipeline(
        notifications.subscribe_push_orchestrator
    )
    unsubscribe_push_pipeline = orchestrator_pipeline(
        notifications.unsubscribe_push_orchestrator
    )
    check_device_pipeline = orchestrator_pipeline(
        notifications.check_device_orchestrator
    )
    resolve_staff_link_pipeline = orchestrator_pipeline(
        notifications.resolve_staff_link_orchestrator
    )
