from app.containers.passkeys.passkey_dependencies import PasskeyDependencies
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


class PasskeyUseCaseFactories:
    """
    One typed factory per passkey use case (W20, migration 1201): Account →
    Security (list, add, rename, remove), the second step of a sign-in and
    a platform admin's enrollment there, and step-up confirmations. Each
    call builds a new use case from the context's dependencies.
    """

    def __init__(self, dependencies: PasskeyDependencies) -> None:
        self._dependencies: PasskeyDependencies = dependencies

    # --- Account → Security.
    def list_passkeys(self) -> UseCaseContract[UserId, PasskeyListView]:
        given = self._dependencies
        return ListPasskeysUseCase(
            passkey_repo=given.passkey_repo,
            user_repo=given.user_repo,
            ceremony=given.ceremony,
        )

    def start_passkey_registration(
        self,
    ) -> UseCaseContract[PasskeyCommand, PasskeyRegistrationView]:
        given = self._dependencies
        return StartPasskeyRegistrationUseCase(
            user_repo=given.user_repo,
            passkey_repo=given.passkey_repo,
            challenge_repo=given.challenge_repo,
            ceremony=given.ceremony,
            step_up=given.step_up,
            wall_clock=given.wall_clock,
            rate_limit_registry=given.rate_limit_registry,
        )

    def finish_passkey_registration(
        self,
    ) -> UseCaseContract[FinishPasskeyRegistrationCommand, PasskeyAddedView]:
        given = self._dependencies
        return FinishPasskeyRegistrationUseCase(
            passkey_repo=given.passkey_repo,
            challenge_repo=given.challenge_repo,
            ceremony=given.ceremony,
            totp_factor_repo=given.totp_factor_repo,
            recovery_code_repo=given.recovery_code_repo,
            user_session_repo=given.user_session_repo,
            session_assurance=given.session_assurance,
            audit_log_repo=given.audit_log_repo,
            wall_clock=given.wall_clock,
        )

    def rename_passkey(self) -> UseCaseContract[RenamePasskeyCommand, PasskeyView]:
        given = self._dependencies
        return RenamePasskeyUseCase(
            passkey_repo=given.passkey_repo, wall_clock=given.wall_clock
        )

    def remove_passkey(self) -> UseCaseContract[RemovePasskeyCommand, None]:
        given = self._dependencies
        return RemovePasskeyUseCase(
            passkey_repo=given.passkey_repo,
            totp_factor_repo=given.totp_factor_repo,
            recovery_code_repo=given.recovery_code_repo,
            user_session_repo=given.user_session_repo,
            step_up=given.step_up,
            audit_log_repo=given.audit_log_repo,
            wall_clock=given.wall_clock,
        )

    # --- The second step of a sign-in, and an admin's first factor there.
    def start_passkey_sign_in(
        self,
    ) -> UseCaseContract[PasskeySignInStepCommand, PasskeyAssertionOptionsView]:
        given = self._dependencies
        return StartPasskeySignInUseCase(
            mfa_challenge_repo=given.mfa_challenge_repo,
            passkey_repo=given.passkey_repo,
            challenge_repo=given.challenge_repo,
            ceremony=given.ceremony,
            wall_clock=given.wall_clock,
            rate_limit_registry=given.rate_limit_registry,
        )

    def verify_passkey_sign_in(
        self,
    ) -> UseCaseContract[VerifyPasskeySignInCommand, LoginSessionView]:
        given = self._dependencies
        return VerifyPasskeySignInUseCase(
            mfa_challenge_repo=given.mfa_challenge_repo,
            user_repo=given.user_repo,
            passkey_repo=given.passkey_repo,
            challenge_repo=given.challenge_repo,
            ceremony=given.ceremony,
            user_session_repo=given.user_session_repo,
            audit_log_repo=given.audit_log_repo,
            user_view_transformer=given.user_view_transformer,
            app_settings=given.app_settings,
            wall_clock=given.wall_clock,
            rate_limit_registry=given.rate_limit_registry,
            product_events=given.product_events,
            platform_admins=given.platform_admins,
            sign_in_notices=given.sign_in_notices,
        )

    def start_passkey_enrollment(
        self,
    ) -> UseCaseContract[PasskeySignInStepCommand, PasskeyRegistrationView]:
        given = self._dependencies
        return StartPasskeyEnrollmentUseCase(
            mfa_challenge_repo=given.mfa_challenge_repo,
            user_repo=given.user_repo,
            totp_factor_repo=given.totp_factor_repo,
            passkey_repo=given.passkey_repo,
            challenge_repo=given.challenge_repo,
            ceremony=given.ceremony,
            wall_clock=given.wall_clock,
            rate_limit_registry=given.rate_limit_registry,
        )

    def finish_passkey_enrollment(
        self,
    ) -> UseCaseContract[FinishPasskeyEnrollmentCommand, LoginSessionView]:
        given = self._dependencies
        return FinishPasskeyEnrollmentUseCase(
            mfa_challenge_repo=given.mfa_challenge_repo,
            user_repo=given.user_repo,
            passkey_repo=given.passkey_repo,
            challenge_repo=given.challenge_repo,
            ceremony=given.ceremony,
            recovery_code_repo=given.recovery_code_repo,
            user_session_repo=given.user_session_repo,
            audit_log_repo=given.audit_log_repo,
            user_view_transformer=given.user_view_transformer,
            app_settings=given.app_settings,
            wall_clock=given.wall_clock,
            rate_limit_registry=given.rate_limit_registry,
            product_events=given.product_events,
            platform_admins=given.platform_admins,
            sign_in_notices=given.sign_in_notices,
        )

    # --- Confirming a sensitive action (step-up) with a passkey.
    def start_passkey_step_up(
        self,
    ) -> UseCaseContract[PasskeyCommand, PasskeyAssertionOptionsView]:
        given = self._dependencies
        return StartPasskeyStepUpUseCase(
            passkey_repo=given.passkey_repo,
            challenge_repo=given.challenge_repo,
            ceremony=given.ceremony,
            session_assurance=given.session_assurance,
            wall_clock=given.wall_clock,
            rate_limit_registry=given.rate_limit_registry,
        )

    def verify_passkey_step_up(
        self,
    ) -> UseCaseContract[VerifyPasskeyStepUpCommand, SessionAssuranceView]:
        given = self._dependencies
        return VerifyPasskeyStepUpUseCase(
            passkey_repo=given.passkey_repo,
            challenge_repo=given.challenge_repo,
            ceremony=given.ceremony,
            user_session_repo=given.user_session_repo,
            session_assurance=given.session_assurance,
            audit_log_repo=given.audit_log_repo,
            app_settings=given.app_settings,
            wall_clock=given.wall_clock,
            rate_limit_registry=given.rate_limit_registry,
        )
