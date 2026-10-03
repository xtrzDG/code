from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.security_orchestrators import (
    SecurityOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class SecurityPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of key management."""

    security_orchestrators: SecurityOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_encryption_keys_pipeline = orchestrator_pipeline(
        security_orchestrators.get_encryption_keys_orchestrator
    )
    start_key_rotation_pipeline = orchestrator_pipeline(
        security_orchestrators.start_key_rotation_orchestrator
    )
    rotate_encrypted_secrets_pipeline = orchestrator_pipeline(
        security_orchestrators.rotate_encrypted_secrets_orchestrator
    )
