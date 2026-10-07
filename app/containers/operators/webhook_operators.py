from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.webhook_pipelines import WebhookPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class WebhookOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the outbound webhooks: the cabinet's endpoints and each
    `deliver_webhook` job in their business's scope; the purge of the
    delivery log across businesses (platform-wide).
    """

    webhook_pipelines: WebhookPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope
    pipelines = webhook_pipelines

    list_webhook_endpoints_operator = pipeline_operator(
        pipelines.list_webhook_endpoints_pipeline, storage_scope
    )
    create_webhook_endpoint_operator = pipeline_operator(
        pipelines.create_webhook_endpoint_pipeline, storage_scope
    )
    update_webhook_endpoint_operator = pipeline_operator(
        pipelines.update_webhook_endpoint_pipeline, storage_scope
    )
    rotate_webhook_secret_operator = pipeline_operator(
        pipelines.rotate_webhook_secret_pipeline, storage_scope
    )
    delete_webhook_endpoint_operator = pipeline_operator(
        pipelines.delete_webhook_endpoint_pipeline, storage_scope
    )
    list_webhook_deliveries_operator = pipeline_operator(
        pipelines.list_webhook_deliveries_pipeline, storage_scope
    )
    get_webhook_delivery_operator = pipeline_operator(
        pipelines.get_webhook_delivery_pipeline, storage_scope
    )
    retry_webhook_delivery_operator = pipeline_operator(
        pipelines.retry_webhook_delivery_pipeline, storage_scope
    )
    send_webhook_test_operator = pipeline_operator(
        pipelines.send_webhook_test_pipeline, storage_scope
    )
    deliver_webhook_operator = pipeline_operator(
        pipelines.deliver_webhook_pipeline, storage_scope
    )
    purge_webhook_deliveries_operator = platform_pipeline_operator(
        pipelines.purge_webhook_deliveries_pipeline, storage_scope
    )
