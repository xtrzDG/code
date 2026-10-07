from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.webhook_orchestrators import (
    WebhookOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class WebhookPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the outbound webhooks (1181)."""

    webhooks: WebhookOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    list_webhook_endpoints_pipeline = orchestrator_pipeline(
        webhooks.list_webhook_endpoints_orchestrator
    )
    create_webhook_endpoint_pipeline = orchestrator_pipeline(
        webhooks.create_webhook_endpoint_orchestrator
    )
    update_webhook_endpoint_pipeline = orchestrator_pipeline(
        webhooks.update_webhook_endpoint_orchestrator
    )
    rotate_webhook_secret_pipeline = orchestrator_pipeline(
        webhooks.rotate_webhook_secret_orchestrator
    )
    delete_webhook_endpoint_pipeline = orchestrator_pipeline(
        webhooks.delete_webhook_endpoint_orchestrator
    )
    list_webhook_deliveries_pipeline = orchestrator_pipeline(
        webhooks.list_webhook_deliveries_orchestrator
    )
    get_webhook_delivery_pipeline = orchestrator_pipeline(
        webhooks.get_webhook_delivery_orchestrator
    )
    retry_webhook_delivery_pipeline = orchestrator_pipeline(
        webhooks.retry_webhook_delivery_orchestrator
    )
    send_webhook_test_pipeline = orchestrator_pipeline(
        webhooks.send_webhook_test_orchestrator
    )
    deliver_webhook_pipeline = orchestrator_pipeline(
        webhooks.deliver_webhook_orchestrator
    )
    purge_webhook_deliveries_pipeline = orchestrator_pipeline(
        webhooks.purge_webhook_deliveries_orchestrator
    )
