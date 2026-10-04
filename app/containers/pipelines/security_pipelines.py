from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.security_orchestrators import (
    SecurityOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class SecurityPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of key management and two-factor sign-in."""

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

    # --- Two-factor sign-in, step-up and a business's requirement.
    verify_mfa_login_pipeline = orchestrator_pipeline(
        security_orchestrators.verify_mfa_login_orchestrator
    )
    start_mfa_login_enrollment_pipeline = orchestrator_pipeline(
        security_orchestrators.start_mfa_login_enrollment_orchestrator
    )
    get_account_security_pipeline = orchestrator_pipeline(
        security_orchestrators.get_account_security_orchestrator
    )
    start_totp_enrollment_pipeline = orchestrator_pipeline(
        security_orchestrators.start_totp_enrollment_orchestrator
    )
    confirm_totp_enrollment_pipeline = orchestrator_pipeline(
        security_orchestrators.confirm_totp_enrollment_orchestrator
    )
    remove_totp_factor_pipeline = orchestrator_pipeline(
        security_orchestrators.remove_totp_factor_orchestrator
    )
    regenerate_recovery_codes_pipeline = orchestrator_pipeline(
        security_orchestrators.regenerate_recovery_codes_orchestrator
    )
    start_step_up_pipeline = orchestrator_pipeline(
        security_orchestrators.start_step_up_orchestrator
    )
    verify_step_up_pipeline = orchestrator_pipeline(
        security_orchestrators.verify_step_up_orchestrator
    )
    get_business_security_pipeline = orchestrator_pipeline(
        security_orchestrators.get_business_security_orchestrator
    )
    update_business_security_pipeline = orchestrator_pipeline(
        security_orchestrators.update_business_security_orchestrator
    )
