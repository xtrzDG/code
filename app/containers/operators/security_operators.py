from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.security_pipelines import SecurityPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class SecurityOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of key management (the platform admin's two routes, and the
    re-encryption job, which walks every business platform-wide) and of
    two-factor sign-in: the person's own routes run unscoped (platform
    collections only), a business's requirement in that business's scope.
    """

    security_pipelines: SecurityPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_encryption_keys_operator = pipeline_operator(
        security_pipelines.get_encryption_keys_pipeline, storage_scope
    )
    start_key_rotation_operator = pipeline_operator(
        security_pipelines.start_key_rotation_pipeline, storage_scope
    )
    rotate_encrypted_secrets_operator = platform_pipeline_operator(
        security_pipelines.rotate_encrypted_secrets_pipeline, storage_scope
    )

    # --- Two-factor sign-in, step-up and a business's requirement.
    verify_mfa_login_operator = pipeline_operator(
        security_pipelines.verify_mfa_login_pipeline, storage_scope
    )
    start_mfa_login_enrollment_operator = pipeline_operator(
        security_pipelines.start_mfa_login_enrollment_pipeline, storage_scope
    )
    get_account_security_operator = pipeline_operator(
        security_pipelines.get_account_security_pipeline, storage_scope
    )
    start_totp_enrollment_operator = pipeline_operator(
        security_pipelines.start_totp_enrollment_pipeline, storage_scope
    )
    confirm_totp_enrollment_operator = pipeline_operator(
        security_pipelines.confirm_totp_enrollment_pipeline, storage_scope
    )
    remove_totp_factor_operator = pipeline_operator(
        security_pipelines.remove_totp_factor_pipeline, storage_scope
    )
    regenerate_recovery_codes_operator = pipeline_operator(
        security_pipelines.regenerate_recovery_codes_pipeline, storage_scope
    )
    start_step_up_operator = pipeline_operator(
        security_pipelines.start_step_up_pipeline, storage_scope
    )
    verify_step_up_operator = pipeline_operator(
        security_pipelines.verify_step_up_pipeline, storage_scope
    )
    get_business_security_operator = pipeline_operator(
        security_pipelines.get_business_security_pipeline, storage_scope
    )
    update_business_security_operator = pipeline_operator(
        security_pipelines.update_business_security_pipeline, storage_scope
    )
