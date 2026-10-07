from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.webhook_use_cases import WebhookUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.integrations.deliver_webhook_orchestrator import (
    DeliverWebhookOrchestrator,
)
from app.orchestrators.integrations.send_webhook_test_orchestrator import (
    SendWebhookTestOrchestrator,
)
from app.schemas.dto.integrations.webhook_views import (
    WebhookDeliveryView,
    WebhookEndpointCommand,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput


class WebhookOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the outbound webhooks (1181): one use case each, but
    the `deliver_webhook` job and "Send test event" (an attempt, then its
    recording).
    """

    webhook_use_cases: WebhookUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    cases = webhook_use_cases

    list_webhook_endpoints_orchestrator = use_case_orchestrator(
        cases.list_webhook_endpoints_use_case
    )
    create_webhook_endpoint_orchestrator = use_case_orchestrator(
        cases.create_webhook_endpoint_use_case
    )
    update_webhook_endpoint_orchestrator = use_case_orchestrator(
        cases.update_webhook_endpoint_use_case
    )
    rotate_webhook_secret_orchestrator = use_case_orchestrator(
        cases.rotate_webhook_secret_use_case
    )
    delete_webhook_endpoint_orchestrator = use_case_orchestrator(
        cases.delete_webhook_endpoint_use_case
    )
    list_webhook_deliveries_orchestrator = use_case_orchestrator(
        cases.list_webhook_deliveries_use_case
    )
    get_webhook_delivery_orchestrator = use_case_orchestrator(
        cases.get_webhook_delivery_use_case
    )
    retry_webhook_delivery_orchestrator = use_case_orchestrator(
        cases.retry_webhook_delivery_use_case
    )
    purge_webhook_deliveries_orchestrator = use_case_orchestrator(
        cases.purge_webhook_deliveries_use_case
    )
    deliver_webhook_orchestrator: Factory[
        OrchestratorContract[QueuedJobInput, JobReport]
    ] = Factory(
        DeliverWebhookOrchestrator,
        attempt_delivery=cases.attempt_webhook_delivery_use_case,
        record_attempt=cases.record_webhook_attempt_use_case,
    )
    send_webhook_test_orchestrator: Factory[
        OrchestratorContract[WebhookEndpointCommand, WebhookDeliveryView]
    ] = Factory(
        SendWebhookTestOrchestrator,
        create_test_delivery=cases.create_webhook_test_delivery_use_case,
        attempt_delivery=cases.attempt_webhook_delivery_use_case,
        record_attempt=cases.record_webhook_attempt_use_case,
    )
