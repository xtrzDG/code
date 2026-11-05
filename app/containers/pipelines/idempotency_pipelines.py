from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.idempotency_orchestrators import (
    IdempotencyOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class IdempotencyPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the idempotency keys of creating requests."""

    idempotency: IdempotencyOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    claim_idempotency_key_pipeline = orchestrator_pipeline(
        idempotency.claim_idempotency_key_orchestrator
    )
    finish_idempotent_request_pipeline = orchestrator_pipeline(
        idempotency.finish_idempotent_request_orchestrator
    )
    purge_idempotency_keys_pipeline = orchestrator_pipeline(
        idempotency.purge_idempotency_keys_orchestrator
    )
