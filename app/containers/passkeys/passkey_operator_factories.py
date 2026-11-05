from app.containers.passkeys.passkey_dependencies import PasskeyDependencies
from app.containers.passkeys.passkey_use_case_factories import (
    PasskeyUseCaseFactories,
)
from app.containers.role_chain_factories import business_scoped_operator
from app.contracts.operator_contract import OperatorContract
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


class PasskeyOperatorFactories:
    """
    One operator per passkey endpoint, each the generic role chain over one
    use case. Their inputs name no business, so they run in the caller's
    scope: unscoped, on the platform collections passkeys live in.
    """

    def __init__(
        self,
        dependencies: PasskeyDependencies,
        use_cases: PasskeyUseCaseFactories,
    ) -> None:
        self._dependencies: PasskeyDependencies = dependencies
        self._use_cases: PasskeyUseCaseFactories = use_cases

    def list_passkeys(self) -> OperatorContract[UserId, PasskeyListView]:
        return business_scoped_operator(
            self._use_cases.list_passkeys(), self._dependencies.storage_scope
        )

    def start_passkey_registration(
        self,
    ) -> OperatorContract[PasskeyCommand, PasskeyRegistrationView]:
        return business_scoped_operator(
            self._use_cases.start_passkey_registration(),
            self._dependencies.storage_scope,
        )

    def finish_passkey_registration(
        self,
    ) -> OperatorContract[FinishPasskeyRegistrationCommand, PasskeyAddedView]:
        return business_scoped_operator(
            self._use_cases.finish_passkey_registration(),
            self._dependencies.storage_scope,
        )

    def rename_passkey(self) -> OperatorContract[RenamePasskeyCommand, PasskeyView]:
        return business_scoped_operator(
            self._use_cases.rename_passkey(), self._dependencies.storage_scope
        )

    def remove_passkey(self) -> OperatorContract[RemovePasskeyCommand, None]:
        return business_scoped_operator(
            self._use_cases.remove_passkey(), self._dependencies.storage_scope
        )

    def start_passkey_sign_in(
        self,
    ) -> OperatorContract[PasskeySignInStepCommand, PasskeyAssertionOptionsView]:
        return business_scoped_operator(
            self._use_cases.start_passkey_sign_in(), self._dependencies.storage_scope
        )

    def verify_passkey_sign_in(
        self,
    ) -> OperatorContract[VerifyPasskeySignInCommand, LoginSessionView]:
        return business_scoped_operator(
            self._use_cases.verify_passkey_sign_in(), self._dependencies.storage_scope
        )

    def start_passkey_enrollment(
        self,
    ) -> OperatorContract[PasskeySignInStepCommand, PasskeyRegistrationView]:
        return business_scoped_operator(
            self._use_cases.start_passkey_enrollment(),
            self._dependencies.storage_scope,
        )

    def finish_passkey_enrollment(
        self,
    ) -> OperatorContract[FinishPasskeyEnrollmentCommand, LoginSessionView]:
        return business_scoped_operator(
            self._use_cases.finish_passkey_enrollment(),
            self._dependencies.storage_scope,
        )

    def start_passkey_step_up(
        self,
    ) -> OperatorContract[PasskeyCommand, PasskeyAssertionOptionsView]:
        return business_scoped_operator(
            self._use_cases.start_passkey_step_up(), self._dependencies.storage_scope
        )

    def verify_passkey_step_up(
        self,
    ) -> OperatorContract[VerifyPasskeyStepUpCommand, SessionAssuranceView]:
        return business_scoped_operator(
            self._use_cases.verify_passkey_step_up(), self._dependencies.storage_scope
        )
