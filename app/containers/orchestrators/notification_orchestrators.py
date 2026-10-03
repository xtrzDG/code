from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.delivery_use_cases import DeliveryUseCasesContainer
from app.containers.use_cases.notification_use_cases import (
    NotificationUseCasesContainer,
)
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.notifications.send_notification_check_orchestrator import (
    SendNotificationCheckOrchestrator,
)
from app.schemas.dto.notifications.notification_settings import (
    ContactCheckCommand,
    NotificationCheckResult,
    PushDeviceCommand,
)


class NotificationOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of Settings → Notifications (checks send through the outbox)."""

    notification_use_cases: NotificationUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    delivery_use_cases: DeliveryUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    list_notification_contacts_orchestrator = use_case_orchestrator(
        notification_use_cases.list_notification_contacts_use_case
    )
    check_contact_orchestrator: Factory[
        OrchestratorContract[ContactCheckCommand, NotificationCheckResult]
    ] = Factory(
        SendNotificationCheckOrchestrator[ContactCheckCommand],
        queue_check=notification_use_cases.queue_contact_check_use_case,
        send_outbound_message=delivery_use_cases.send_outbound_message_use_case,
        record_outbound_attempt=delivery_use_cases.record_outbound_attempt_use_case,
    )
    get_notification_settings_orchestrator = use_case_orchestrator(
        notification_use_cases.get_notification_settings_use_case
    )
    update_notification_preferences_orchestrator = use_case_orchestrator(
        notification_use_cases.update_notification_preferences_use_case
    )
    subscribe_push_orchestrator = use_case_orchestrator(
        notification_use_cases.subscribe_push_use_case
    )
    unsubscribe_push_orchestrator = use_case_orchestrator(
        notification_use_cases.unsubscribe_push_use_case
    )
    check_device_orchestrator: Factory[
        OrchestratorContract[PushDeviceCommand, NotificationCheckResult]
    ] = Factory(
        SendNotificationCheckOrchestrator[PushDeviceCommand],
        queue_check=notification_use_cases.queue_device_check_use_case,
        send_outbound_message=delivery_use_cases.send_outbound_message_use_case,
        record_outbound_attempt=delivery_use_cases.record_outbound_attempt_use_case,
    )
    resolve_staff_link_orchestrator = use_case_orchestrator(
        notification_use_cases.resolve_staff_link_use_case
    )
