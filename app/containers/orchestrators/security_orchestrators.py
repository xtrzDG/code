from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.mfa_use_cases import MfaUseCasesContainer
from app.containers.use_cases.security_use_cases import SecurityUseCasesContainer


class SecurityOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of key management and two-factor sign-in (one use case each)."""

    security_use_cases: SecurityUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    mfa_use_cases: MfaUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_encryption_keys_orchestrator = use_case_orchestrator(
        security_use_cases.get_encryption_keys_use_case
    )
    start_key_rotation_orchestrator = use_case_orchestrator(
        security_use_cases.start_key_rotation_use_case
    )
    rotate_encrypted_secrets_orchestrator = use_case_orchestrator(
        security_use_cases.rotate_encrypted_secrets_use_case
    )

    # --- Two-factor sign-in, step-up and a business's requirement.
    verify_mfa_login_orchestrator = use_case_orchestrator(
        mfa_use_cases.verify_mfa_login_use_case
    )
    start_mfa_login_enrollment_orchestrator = use_case_orchestrator(
        mfa_use_cases.start_mfa_login_enrollment_use_case
    )
    get_account_security_orchestrator = use_case_orchestrator(
        mfa_use_cases.get_account_security_use_case
    )
    start_totp_enrollment_orchestrator = use_case_orchestrator(
        mfa_use_cases.start_totp_enrollment_use_case
    )
    confirm_totp_enrollment_orchestrator = use_case_orchestrator(
        mfa_use_cases.confirm_totp_enrollment_use_case
    )
    remove_totp_factor_orchestrator = use_case_orchestrator(
        mfa_use_cases.remove_totp_factor_use_case
    )
    regenerate_recovery_codes_orchestrator = use_case_orchestrator(
        mfa_use_cases.regenerate_recovery_codes_use_case
    )
    start_step_up_orchestrator = use_case_orchestrator(
        mfa_use_cases.start_step_up_use_case
    )
    verify_step_up_orchestrator = use_case_orchestrator(
        mfa_use_cases.verify_step_up_use_case
    )
    get_business_security_orchestrator = use_case_orchestrator(
        mfa_use_cases.get_business_security_use_case
    )
    update_business_security_orchestrator = use_case_orchestrator(
        mfa_use_cases.update_business_security_use_case
    )

    # --- Device sessions, the admin team and support access (1103).
    list_my_sessions_orchestrator = use_case_orchestrator(
        mfa_use_cases.list_my_sessions_use_case
    )
    revoke_session_orchestrator = use_case_orchestrator(
        mfa_use_cases.revoke_session_use_case
    )
    revoke_other_sessions_orchestrator = use_case_orchestrator(
        mfa_use_cases.revoke_other_sessions_use_case
    )
    list_platform_admins_orchestrator = use_case_orchestrator(
        security_use_cases.list_platform_admins_use_case
    )
    add_platform_admin_orchestrator = use_case_orchestrator(
        security_use_cases.add_platform_admin_use_case
    )
    change_platform_admin_role_orchestrator = use_case_orchestrator(
        security_use_cases.change_platform_admin_role_use_case
    )
    remove_platform_admin_orchestrator = use_case_orchestrator(
        security_use_cases.remove_platform_admin_use_case
    )
    close_client_cabinet_orchestrator = use_case_orchestrator(
        security_use_cases.close_client_cabinet_use_case
    )
    end_expired_support_access_orchestrator = use_case_orchestrator(
        security_use_cases.end_expired_support_access_use_case
    )
    get_support_access_orchestrator = use_case_orchestrator(
        security_use_cases.get_support_access_use_case
    )
    update_support_write_access_orchestrator = use_case_orchestrator(
        security_use_cases.update_support_write_access_use_case
    )
    end_support_access_orchestrator = use_case_orchestrator(
        security_use_cases.end_support_access_use_case
    )
