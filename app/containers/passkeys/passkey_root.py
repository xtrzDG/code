from functools import cached_property

from app.containers.passkeys.passkey_dependencies import PasskeyDependencies
from app.containers.passkeys.passkey_operator_factories import (
    PasskeyOperatorFactories,
)
from app.containers.passkeys.passkey_use_case_factories import (
    PasskeyUseCaseFactories,
)


class PasskeyRoot:
    """
    The typed composition root of the passkey context (ADR 0010, like
    app/containers/feedback/): plain Python that builds its use cases and
    their operators from PasskeyDependencies, checked by mypy and pyright
    without a single `# type: ignore`. The dependency graph holds one root
    (UseCasesContainer.passkey_root) and exposes the operators the routers
    call (SecurityOperatorsContainer).
    """

    def __init__(self, dependencies: PasskeyDependencies) -> None:
        self._dependencies: PasskeyDependencies = dependencies

    @cached_property
    def use_cases(self) -> PasskeyUseCaseFactories:
        return PasskeyUseCaseFactories(self._dependencies)

    @cached_property
    def operators(self) -> PasskeyOperatorFactories:
        return PasskeyOperatorFactories(self._dependencies, self.use_cases)
