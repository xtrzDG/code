from app.containers.account_deletion.account_deletion_dependencies import (
    AccountDeletionDependencies,
)
from app.containers.account_deletion.closure_use_case_factories import (
    ClosureUseCaseFactories,
)
from app.containers.account_deletion.deletion_use_case_factories import (
    DeletionUseCaseFactories,
)
from app.containers.role_chain_factories import (
    business_scoped_operator,
    platform_wide_operator,
)
from app.contracts.operator_contract import OperatorContract
from app.schemas.dto.business_closures.account_deletion import (
    DeleteCurrentUserCommand,
)
from app.schemas.dto.business_closures.business_deletions import (
    BusinessDeletionList,
    DeletionCertificateFile,
    DeletionCertificateQuery,
)
from app.schemas.dto.business_closures.closure_views import (
    BusinessClosureView,
    CancelBusinessClosureCommand,
    CloseBusinessCommand,
)
from app.schemas.dto.businesses import BusinessQuery
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.typings.users.prefixed_id import UserId


class AccountDeletionOperatorFactories:
    """
    One operator per endpoint and job, each the generic role chain over one
    use case. The closure's endpoints run in the scope of their business;
    a person's account and certificates name no business (platform
    collections, the caller's scope); the sweep, the offboarding, the
    deletion job and the ledger applied again run platform-wide (the
    platform pool: the deletion reaches every row of the business, whatever
    its table).
    """

    def __init__(
        self,
        dependencies: AccountDeletionDependencies,
        closures: ClosureUseCaseFactories,
        deletions: DeletionUseCaseFactories,
    ) -> None:
        self._scope = dependencies.storage_scope
        self._closures: ClosureUseCaseFactories = closures
        self._deletions: DeletionUseCaseFactories = deletions

    def get_business_closure(
        self,
    ) -> OperatorContract[BusinessQuery, BusinessClosureView]:
        return business_scoped_operator(
            self._closures.get_business_closure(), self._scope
        )

    def close_business(
        self,
    ) -> OperatorContract[CloseBusinessCommand, BusinessClosureView]:
        return business_scoped_operator(self._closures.close_business(), self._scope)

    def cancel_business_closure(
        self,
    ) -> OperatorContract[CancelBusinessClosureCommand, None]:
        return business_scoped_operator(
            self._closures.cancel_business_closure(), self._scope
        )

    def queue_due_deletions(self) -> OperatorContract[JobTick, JobReport]:
        return platform_wide_operator(self._closures.queue_due_deletions(), self._scope)

    def offboard_unpaid_businesses(self) -> OperatorContract[JobTick, JobReport]:
        return platform_wide_operator(
            self._closures.offboard_unpaid_businesses(), self._scope
        )

    def delete_business(self) -> OperatorContract[QueuedJobInput, JobReport]:
        return platform_wide_operator(self._deletions.delete_business(), self._scope)

    def reapply_deletion_ledger(self) -> OperatorContract[JobTick, JobReport]:
        return platform_wide_operator(
            self._deletions.reapply_deletion_ledger(), self._scope
        )

    def list_business_deletions(
        self,
    ) -> OperatorContract[UserId, BusinessDeletionList]:
        return business_scoped_operator(
            self._deletions.list_business_deletions(), self._scope
        )

    def get_deletion_certificate(
        self,
    ) -> OperatorContract[DeletionCertificateQuery, DeletionCertificateFile]:
        return business_scoped_operator(
            self._deletions.get_deletion_certificate(), self._scope
        )

    def delete_current_user(
        self,
    ) -> OperatorContract[DeleteCurrentUserCommand, None]:
        return business_scoped_operator(
            self._deletions.delete_current_user(), self._scope
        )
