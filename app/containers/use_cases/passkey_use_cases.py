from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.mfa import SessionAssuranceView
from app.schemas.dto.passkeys import (
    FinishPasskeyEnrollmentCommand,
    FinishPasskeyRegistrationCommand,
    PasskeyAddedView,
    PasskeyAssertionOptionsView,
    PasskeyCommand,
    PasskeyListView,
    PasskeyRegistrationView,
    PasskeySignInStepCommand,
    PasskeyView,
    RemovePasskeyCommand,
    RenamePasskeyCommand,
    VerifyPasskeySignInCommand,
    VerifyPasskeyStepUpCommand,
)
from app.schemas.dto.users import LoginSessionView
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.users.passkeys.finish_passkey_enrollment_use_case import (
    FinishPasskeyEnrollmentUseCase,
)
from app.use_cases.users.passkeys.finish_passkey_registration_use_case import (
    FinishPasskeyRegistrationUseCase,
)
from app.use_cases.users.passkeys.list_passkeys_use_case import ListPasskeysUseCase
from app.use_cases.users.passkeys.remove_passkey_use_case import RemovePasskeyUseCase
from app.use_cases.users.passkeys.rename_passkey_use_case import RenamePasskeyUseCase
from app.use_cases.users.passkeys.start_passkey_enrollment_use_case import (
    StartPasskeyEnrollmentUseCase,
)
from app.use_cases.users.passkeys.start_passkey_registration_use_case import (
    StartPasskeyRegistrationUseCase,
)
from app.use_cases.users.passkeys.start_passkey_sign_in_use_case import (
    StartPasskeySignInUseCase,
)
from app.use_cases.users.passkeys.start_passkey_step_up_use_case import (
    StartPasskeyStepUpUseCase,
)
from app.use_cases.users.passkeys.verify_passkey_sign_in_use_case import (
    VerifyPasskeySignInUseCase,
)
from app.use_cases.users.passkeys.verify_passkey_step_up_use_case import (
    VerifyPasskeyStepUpUseCase,
)


class PasskeyUseCasesContainer(containers.DeclarativeContainer):
    """
    Passkeys (W20, migration 1201): Account → Security (list, add, rename,
    remove), the second step of a sign-in, a platform admin's first factor
    at sign-in, and step-up confirmations.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Account → Security.
    list_passkeys_use_case: Factory[UseCaseContract[UserId, PasskeyListView]] = Factory(
        ListPasskeysUseCase,
        passkey_repo=repositories.passkey_repo,
        user_repo=repositories.user_repo,
        ceremony=adapters.passkey_ceremony,
    )
    start_passkey_registration_use_case: Factory[
        UseCaseContract[PasskeyCommand, PasskeyRegistrationView]
    ] = Factory(
        StartPasskeyRegistrationUseCase,
        user_repo=repositories.user_repo,
        passkey_repo=repositories.passkey_repo,
        challenge_repo=repositories.passkey_challenge_repo,
        ceremony=adapters.passkey_ceremony,
        step_up=utilities.step_up_guard,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    finish_passkey_registration_use_case: Factory[
        UseCaseContract[FinishPasskeyRegistrationCommand, PasskeyAddedView]
    ] = Factory(
        FinishPasskeyRegistrationUseCase,
        passkey_repo=repositories.passkey_repo,
        challenge_repo=repositories.passkey_challenge_repo,
        ceremony=adapters.passkey_ceremony,
        totp_factor_repo=repositories.totp_factor_repo,
        recovery_code_repo=repositories.recovery_code_repo,
        user_session_repo=repositories.user_session_repo,
        session_assurance=utilities.session_assurance,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    rename_passkey_use_case: Factory[
        UseCaseContract[RenamePasskeyCommand, PasskeyView]
    ] = Factory(
        RenamePasskeyUseCase,
        passkey_repo=repositories.passkey_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    remove_passkey_use_case: Factory[UseCaseContract[RemovePasskeyCommand, None]] = (
        Factory(
            RemovePasskeyUseCase,
            passkey_repo=repositories.passkey_repo,
            totp_factor_repo=repositories.totp_factor_repo,
            recovery_code_repo=repositories.recovery_code_repo,
            user_session_repo=repositories.user_session_repo,
            step_up=utilities.step_up_guard,
            audit_log_repo=repositories.audit_log_repo,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )

    # --- The second step of a sign-in, and an admin's first factor there.
    start_passkey_sign_in_use_case: Factory[
        UseCaseContract[PasskeySignInStepCommand, PasskeyAssertionOptionsView]
    ] = Factory(
        StartPasskeySignInUseCase,
        mfa_challenge_repo=repositories.mfa_challenge_repo,
        passkey_repo=repositories.passkey_repo,
        challenge_repo=repositories.passkey_challenge_repo,
        ceremony=adapters.passkey_ceremony,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
    )
    verify_passkey_sign_in_use_case: Factory[
        UseCaseContract[VerifyPasskeySignInCommand, LoginSessionView]
    ] = Factory(
        VerifyPasskeySignInUseCase,
        mfa_challenge_repo=repositories.mfa_challenge_repo,
        user_repo=repositories.user_repo,
        passkey_repo=repositories.passkey_repo,
        challenge_repo=repositories.passkey_challenge_repo,
        ceremony=adapters.passkey_ceremony,
        user_session_repo=repositories.user_session_repo,
        audit_log_repo=repositories.audit_log_repo,
        user_view_transformer=transformers.user_view_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
        product_events=facilitators.product_events,
        platform_admins=registries.platform_admin_registry,
        sign_in_notices=facilitators.sign_in_notice_facilitator,
    )
    start_passkey_enrollment_use_case: Factory[
        UseCaseContract[PasskeySignInStepCommand, PasskeyRegistrationView]
    ] = Factory(
        StartPasskeyEnrollmentUseCase,
        mfa_challenge_repo=repositories.mfa_challenge_repo,
        user_repo=repositories.user_repo,
        totp_factor_repo=repositories.totp_factor_repo,
        passkey_repo=repositories.passkey_repo,
        challenge_repo=repositories.passkey_challenge_repo,
        ceremony=adapters.passkey_ceremony,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
    )
    finish_passkey_enrollment_use_case: Factory[
        UseCaseContract[FinishPasskeyEnrollmentCommand, LoginSessionView]
    ] = Factory(
        FinishPasskeyEnrollmentUseCase,
        mfa_challenge_repo=repositories.mfa_challenge_repo,
        user_repo=repositories.user_repo,
        passkey_repo=repositories.passkey_repo,
        challenge_repo=repositories.passkey_challenge_repo,
        ceremony=adapters.passkey_ceremony,
        recovery_code_repo=repositories.recovery_code_repo,
        user_session_repo=repositories.user_session_repo,
        audit_log_repo=repositories.audit_log_repo,
        user_view_transformer=transformers.user_view_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
        product_events=facilitators.product_events,
        platform_admins=registries.platform_admin_registry,
        sign_in_notices=facilitators.sign_in_notice_facilitator,
    )

    # --- Confirming a sensitive action (step-up) with a passkey.
    start_passkey_step_up_use_case: Factory[
        UseCaseContract[PasskeyCommand, PasskeyAssertionOptionsView]
    ] = Factory(
        StartPasskeyStepUpUseCase,
        passkey_repo=repositories.passkey_repo,
        challenge_repo=repositories.passkey_challenge_repo,
        ceremony=adapters.passkey_ceremony,
        session_assurance=utilities.session_assurance,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
    )
    verify_passkey_step_up_use_case: Factory[
        UseCaseContract[VerifyPasskeyStepUpCommand, SessionAssuranceView]
    ] = Factory(
        VerifyPasskeyStepUpUseCase,
        passkey_repo=repositories.passkey_repo,
        challenge_repo=repositories.passkey_challenge_repo,
        ceremony=adapters.passkey_ceremony,
        user_session_repo=repositories.user_session_repo,
        session_assurance=utilities.session_assurance,
        audit_log_repo=repositories.audit_log_repo,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        rate_limit_registry=registries.request_rate_limit_registry,
    )
