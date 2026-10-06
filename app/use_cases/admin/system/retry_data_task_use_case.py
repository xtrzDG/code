from typed_time_provider import Microseconds, WallClock

from app.contracts.data_tasks import DataTaskRegistryContract, DataTaskStateRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.maintenance import DataTaskStatus
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.data_tasks import (
    DataTaskDefinition,
    RetryDataTaskCommand,
    RetryDataTaskResult,
)
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.admin.system.data_task_views import build_data_task_view
from app.utilities.maintenance.data_task_progress import walk_again
from app.utilities.maintenance.data_task_status import effective_status

DATA_TASK_AUDIT_ENTITY: AuditEntityName = AuditEntityName("data_task")


class RetryDataTaskUseCase(UseCaseContract[RetryDataTaskCommand, RetryDataTaskResult]):
    """
    A platform admin asks the batch worker to walk a FAILED data task again
    (after fixing the rows it could not upgrade, say): it turns PENDING
    from the start of its table, still due since it first became due, and
    the next run of `run_data_tasks` takes it. The change is one atomic
    step on the stored state, so it never overwrites a run's progress.
    Written to the audit log (UPDATE of the data task).

    Raises:
        AccessDeniedError: the user may not manage operations.
        NotFoundError: no such task in this release's registry.
        ConflictError: the task is not FAILED (it runs, waits or is done).
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        registry: DataTaskRegistryContract,
        state_repo: DataTaskStateRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._registry: DataTaskRegistryContract = registry
        self._state_repo: DataTaskStateRepoContract = state_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RetryDataTaskCommand) -> RetryDataTaskResult:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        task: DataTaskDefinition | None = self._registry.find_task(input_data.key)
        if task is None:
            raise NotFoundError(f"There is no data task {input_data.key}.")

        now: Microseconds = self._wall_clock.now_unix()

        def retry(state: DataTaskStateDocument) -> DataTaskStateDocument:
            status: DataTaskStatus = effective_status(task, state)
            if status is not DataTaskStatus.FAILED:
                raise ConflictError(
                    f"Data task {task.key} is {status.value}; only a failed task "
                    "is walked again."
                )

            return walk_again(task, state, now)

        retried: DataTaskStateDocument | None = self._state_repo.modify(task.key, retry)
        if retried is None:
            raise ConflictError(
                f"Data task {task.key} has not run yet; only a failed task is "
                "walked again."
            )

        entry = AuditLogEntryDocument(
            actor_id=admin.id,
            action=AuditAction.UPDATE,
            entity=DATA_TASK_AUDIT_ENTITY,
            entity_id=AuditEntityReference(str(task.key)),
            ip_address=input_data.client_ip_address,
            created_at=now,
            updated_at=now,
        )
        self._audit_log_repo.append(entry)
        return RetryDataTaskResult(
            task=build_data_task_view(task, retried, {}, now),
            audit_log_entry_id=entry.id,
        )
