from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.idempotency_use_cases import (
    IdempotencyUseCasesContainer,
)


class IdempotencyOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the idempotency keys of creating requests."""

    idempotency_use_cases: IdempotencyUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    claim_idempotency_key_orchestrator = use_case_orchestrator(
        idempotency_use_cases.claim_idempotency_key_use_case
    )
    finish_idempotent_request_orchestrator = use_case_orchestrator(
        idempotency_use_cases.finish_idempotent_request_use_case
    )
    purge_idempotency_keys_orchestrator = use_case_orchestrator(
        idempotency_use_cases.purge_idempotency_keys_use_case
    )
