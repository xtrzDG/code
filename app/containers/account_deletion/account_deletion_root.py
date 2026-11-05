from functools import cached_property

from app.containers.account_deletion.account_deletion_dependencies import (
    AccountDeletionDependencies,
)
from app.containers.account_deletion.account_deletion_operator_factories import (
    AccountDeletionOperatorFactories,
)
from app.containers.account_deletion.closure_use_case_factories import (
    ClosureUseCaseFactories,
)
from app.containers.account_deletion.deletion_use_case_factories import (
    DeletionUseCaseFactories,
)


class AccountDeletionRoot:
    """
    The typed composition root of closing and deleting businesses and
    accounts (R15-ACCOUNT-DELETION, ADR 0010): plain Python that builds the
    use cases and their operators from AccountDeletionDependencies, checked
    by mypy and pyright without a single `# type: ignore`. The dependency
    graph holds one root (UseCasesContainer.account_deletion_root); the
    routers, the queued job and the periodic jobs take its operators.
    """

    def __init__(self, dependencies: AccountDeletionDependencies) -> None:
        self._dependencies: AccountDeletionDependencies = dependencies

    @cached_property
    def closures(self) -> ClosureUseCaseFactories:
        return ClosureUseCaseFactories(self._dependencies)

    @cached_property
    def deletions(self) -> DeletionUseCaseFactories:
        return DeletionUseCaseFactories(self._dependencies)

    @cached_property
    def operators(self) -> AccountDeletionOperatorFactories:
        return AccountDeletionOperatorFactories(
            self._dependencies, self.closures, self.deletions
        )
