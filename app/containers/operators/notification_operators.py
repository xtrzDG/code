from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.notification_pipelines import (
    NotificationPipelinesContainer,
)
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class NotificationOperatorsContainer(containers.DeclarativeContainer):
    """Operators of Settings → Notifications, each in its business's scope."""

    notification_pipelines: NotificationPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    list_notification_contacts_operator = pipeline_operator(
        notification_pipelines.list_notification_contacts_pipeline, storage_scope
    )
    check_contact_operator = pipeline_operator(
        notification_pipelines.check_contact_pipeline, storage_scope
    )
    get_notification_settings_operator = pipeline_operator(
        notification_pipelines.get_notification_settings_pipeline, storage_scope
    )
    update_notification_preferences_operator = pipeline_operator(
        notification_pipelines.update_notification_preferences_pipeline, storage_scope
    )
    subscribe_push_operator = pipeline_operator(
        notification_pipelines.subscribe_push_pipeline, storage_scope
    )
    unsubscribe_push_operator = pipeline_operator(
        notification_pipelines.unsubscribe_push_pipeline, storage_scope
    )
    check_device_operator = pipeline_operator(
        notification_pipelines.check_device_pipeline, storage_scope
    )
    resolve_staff_link_operator = pipeline_operator(
        notification_pipelines.resolve_staff_link_pipeline, storage_scope
    )
