from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.security_use_cases import SecurityUseCasesContainer


class SecurityOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of key management (one use case each)."""

    security_use_cases: SecurityUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_encryption_keys_orchestrator = use_case_orchestrator(
        security_use_cases.get_encryption_keys_use_case
    )
    start_key_rotation_orchestrator = use_case_orchestrator(
        security_use_cases.start_key_rotation_use_case
    )
    rotate_encrypted_secrets_orchestrator = use_case_orchestrator(
        security_use_cases.rotate_encrypted_secrets_use_case
    )
