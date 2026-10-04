from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.mfa import (
    AccountSecurityView,
    BusinessSecurityView,
    ConfirmTotpCommand,
    MfaChangeCommand,
    RecoveryCodesView,
    SessionAssuranceView,
    StartMfaEnrollmentCommand,
    StartStepUpCommand,
    StepUpChallengeView,
    TotpEnrollmentView,
    UpdateBusinessSecurityCommand,
    VerifyMfaLoginCommand,
    VerifyStepUpCommand,
)
from app.schemas.dto.users import LoginSessionView
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.businesses.security.get_business_security_use_case import (
    GetBusinessSecurityUseCase,
)
from app.use_cases.businesses.security.update_business_security_use_case import (
    UpdateBusinessSecurityUseCase,
)
from app.use_cases.users.mfa.confirm_totp_enrollment_use_case import (
    ConfirmTotpEnrollmentUseCase,
)
from app.use_cases.users.mfa.get_account_security_use_case import (
    GetAccountSecurityUseCase,
)
from app.use_cases.users.mfa.regenerate_recovery_codes_use_case import (
    RegenerateRecoveryCodesUseCase,
)
from app.use_cases.users.mfa.remove_totp_factor_use_case import (
    RemoveTotpFactorUseCase,
)
from app.use_cases.users.mfa.start_mfa_login_enrollment_use_case import (
    StartMfaLoginEnrollmentUseCase,
)
from app.use_cases.users.mfa.start_step_up_use_case import StartStepUpUseCase
from app.use_cases.users.mfa.start_totp_enrollment_use_case import (
    StartTotpEnrollmentUseCase,
)
from app.use_cases.users.mfa.verify_mfa_login_use_case import VerifyMfaLoginUseCase
from app.use_cases.users.mfa.verify_step_up_use_case import VerifyStepUpUseCase


class MfaUseCasesContainer(containers.DeclarativeContainer):
    """
    Two-factor sign-in: the second step of a sign-in (and an admin's first
    authenticator), Account → Security, confirming sensitive actions
    (step-up) and a business's two-factor requirement.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- The second step of a sign-in.
    verify_mfa_login_use_case: Factory[
        UseCaseContract[VerifyMfaLoginCommand, LoginSessionView]
    ] = Factory(
        VerifyMfaLoginUseCase,
        mfa_challenge_repo=repositories.mfa_challenge_repo,
        user_repo=repositories.user_repo,
        totp_factor_repo=repositories.totp_factor_repo,
        recovery_code_repo=repositories.recovery_code_repo,
        totp_secret_cipher=adapters.totp_secret_cipher,
        user_session_repo=repositories.user_session_repo,
        audit_log_repo=repositories.audit_log_repo,
        user_view_transformer=transformers.user_view_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
        product_events=facilitators.product_events,
    )
    start_mfa_login_enrollment_use_case: Factory[
        UseCaseContract[StartMfaEnrollmentCommand, TotpEnrollmentView]
    ] = Factory(
        StartMfaLoginEnrollmentUseCase,
        mfa_challenge_repo=repositories.mfa_challenge_repo,
        user_repo=repositories.user_repo,
        totp_factor_repo=repositories.totp_factor_repo,
        totp_secret_cipher=adapters.totp_secret_cipher,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
    )

    # --- Account → Security.
    get_account_security_use_case: Factory[
        UseCaseContract[UserId, AccountSecurityView]
    ] = Factory(
        GetAccountSecurityUseCase,
        user_repo=repositories.user_repo,
        totp_factor_repo=repositories.totp_factor_repo,
        recovery_code_repo=repositories.recovery_code_repo,
        session_assurance=utilities.session_assurance,
        app_settings=config.app_settings,
    )
    start_totp_enrollment_use_case: Factory[
        UseCaseContract[UserId, TotpEnrollmentView]
    ] = Factory(
        StartTotpEnrollmentUseCase,
        user_repo=repositories.user_repo,
        totp_factor_repo=repositories.totp_factor_repo,
        totp_secret_cipher=adapters.totp_secret_cipher,
        step_up=utilities.step_up_guard,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    confirm_totp_enrollment_use_case: Factory[
        UseCaseContract[ConfirmTotpCommand, RecoveryCodesView]
    ] = Factory(
        ConfirmTotpEnrollmentUseCase,
        totp_factor_repo=repositories.totp_factor_repo,
        recovery_code_repo=repositories.recovery_code_repo,
        totp_secret_cipher=adapters.totp_secret_cipher,
        user_session_repo=repositories.user_session_repo,
        session_assurance=utilities.session_assurance,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    remove_totp_factor_use_case: Factory[UseCaseContract[MfaChangeCommand, None]] = (
        Factory(
            RemoveTotpFactorUseCase,
            totp_factor_repo=repositories.totp_factor_repo,
            recovery_code_repo=repositories.recovery_code_repo,
            user_session_repo=repositories.user_session_repo,
            session_assurance=utilities.session_assurance,
            step_up=utilities.step_up_guard,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    regenerate_recovery_codes_use_case: Factory[
        UseCaseContract[MfaChangeCommand, RecoveryCodesView]
    ] = Factory(
        RegenerateRecoveryCodesUseCase,
        totp_factor_repo=repositories.totp_factor_repo,
        recovery_code_repo=repositories.recovery_code_repo,
        step_up=utilities.step_up_guard,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Confirming a sensitive action (step-up).
    start_step_up_use_case: Factory[
        UseCaseContract[StartStepUpCommand, StepUpChallengeView]
    ] = Factory(
        StartStepUpUseCase,
        user_repo=repositories.user_repo,
        totp_factor_repo=repositories.totp_factor_repo,
        start_otp_login=account_use_cases.start_otp_login_use_case,
    )
    verify_step_up_use_case: Factory[
        UseCaseContract[VerifyStepUpCommand, SessionAssuranceView]
    ] = Factory(
        VerifyStepUpUseCase,
        user_repo=repositories.user_repo,
        totp_factor_repo=repositories.totp_factor_repo,
        recovery_code_repo=repositories.recovery_code_repo,
        totp_secret_cipher=adapters.totp_secret_cipher,
        otp_challenge_repo=repositories.otp_challenge_repo,
        user_session_repo=repositories.user_session_repo,
        session_assurance=utilities.session_assurance,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
    )

    # --- A business's two-factor requirement for its team.
    get_business_security_use_case: Factory[
        UseCaseContract[BusinessQuery, BusinessSecurityView]
    ] = Factory(
        GetBusinessSecurityUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        totp_factor_repo=repositories.totp_factor_repo,
        session_assurance=utilities.session_assurance,
    )
    update_business_security_use_case: Factory[
        UseCaseContract[UpdateBusinessSecurityCommand, BusinessSecurityView]
    ] = Factory(
        UpdateBusinessSecurityUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        business_repo=repositories.business_repo,
        totp_factor_repo=repositories.totp_factor_repo,
        session_assurance=utilities.session_assurance,
        step_up=utilities.step_up_guard,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
