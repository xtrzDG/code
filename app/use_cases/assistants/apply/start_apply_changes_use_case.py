from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.setup_repositories import AssistantApplyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.setup import ApplyChangesStage
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.setup import AssistantApplyDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.apply_changes import ApplyChangesCommand, ApplyStart
from app.schemas.dto.setup.pending_changes import PendingChange, PendingChangesRequest
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.assistants.apply.apply_records import (
    announce_apply,
    is_apply_running,
)
from app.utilities.setup.setup_keys import derive_assistant_apply_id

APPLY_AUDIT_ENTITY: AuditEntityName = AuditEntityName("assistant_apply")


class StartApplyChangesUseCase(UseCaseContract[ApplyChangesCommand, ApplyStart]):
    """
    The owner presses "Apply changes": register the apply and say how it
    goes on. Idempotent: while an apply is under way (building, checking,
    publishing) the same one is returned and nothing new starts; when the
    live version already has everything, nothing starts either. A version
    already checked (READY) and built from what the business has now is
    published without building and checking it again; otherwise a new
    version is built. Starting is atomic, so two presses at once start one
    apply, and it is written to the audit log.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_apply_repo: AssistantApplyRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        collect_pending_changes: UseCaseContract[
            PendingChangesRequest, list[PendingChange]
        ],
        audit_log_repo: AuditLogRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_apply_repo: AssistantApplyRepoContract = assistant_apply_repo
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._collect_pending_changes: UseCaseContract[
            PendingChangesRequest, list[PendingChange]
        ] = collect_pending_changes
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ApplyChangesCommand) -> ApplyStart:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        versions: list[AssistantVersionDocument] = (
            self._assistant_version_repo.list_by_business(business.id)
        )
        current: AssistantApplyDocument | None = (
            self._assistant_apply_repo.get_by_business(business.id)
        )
        if current is not None and is_apply_running(current, versions, now):
            return ApplyStart(business=business, apply=current, is_new=False)

        latest: AssistantVersionDocument | None = versions[-1] if versions else None
        is_up_to_date: bool = latest is not None and not self._has_changes(
            business, latest
        )
        if (
            is_up_to_date
            and latest is not None
            and latest.status is AssistantVersionStatus.PUBLISHED
        ):
            live: AssistantApplyDocument = current or self._record_live(
                business, latest, input_data, now
            )
            return ApplyStart(business=business, apply=live, is_new=False)

        reused: AssistantVersionDocument | None = (
            latest
            if is_up_to_date
            and latest is not None
            and latest.status is AssistantVersionStatus.READY
            else None
        )
        fresh = AssistantApplyDocument(
            id=derive_assistant_apply_id(business.id),
            business_id=business.id,
            stage=(
                ApplyChangesStage.BUILDING
                if reused is None
                else ApplyChangesStage.PUBLISHING
            ),
            requested_by=input_data.user_id,
            assistant_version_id=None if reused is None else reused.id,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        started: AssistantApplyDocument | None = self._register(
            business, fresh, versions, now
        )
        if started is None:
            running: AssistantApplyDocument = (
                self._assistant_apply_repo.get_by_business(business.id) or fresh
            )
            return ApplyStart(business=business, apply=running, is_new=False)

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.CREATE,
                entity=APPLY_AUDIT_ENTITY,
                entity_id=AuditEntityReference(str(started.id)),
                created_at=now,
                updated_at=now,
            )
        )
        announce_apply(self._live_events, started)
        return ApplyStart(
            business=business,
            apply=started,
            version_to_publish=None if reused is None else reused.id,
            is_new=True,
        )

    def _register(
        self,
        business: BusinessDocument,
        fresh: AssistantApplyDocument,
        versions: list[AssistantVersionDocument],
        now: Microseconds,
    ) -> AssistantApplyDocument | None:
        """The new apply, or None when another one got under way first."""

        if self._assistant_apply_repo.insert_if_absent(fresh):
            return fresh

        def replace(stored: AssistantApplyDocument) -> AssistantApplyDocument | None:
            if is_apply_running(stored, versions, now):
                return None

            return fresh.model_copy(update={"created_at": stored.created_at})

        return self._assistant_apply_repo.modify(business.id, replace)

    def _record_live(
        self,
        business: BusinessDocument,
        version: AssistantVersionDocument,
        command: ApplyChangesCommand,
        now: Microseconds,
    ) -> AssistantApplyDocument:
        """An apply that finds everything live already: nothing to do."""

        live = AssistantApplyDocument(
            id=derive_assistant_apply_id(business.id),
            business_id=business.id,
            stage=ApplyChangesStage.LIVE,
            requested_by=command.user_id,
            assistant_version_id=version.id,
            started_at=now,
            finished_at=now,
            created_at=now,
            updated_at=now,
        )
        self._assistant_apply_repo.insert_if_absent(live)
        return self._assistant_apply_repo.get_by_business(business.id) or live

    def _has_changes(
        self,
        business: BusinessDocument,
        version: AssistantVersionDocument,
    ) -> bool:
        if self._business_profile_repo.get_by_business(business.id) is None:
            return False

        return bool(
            self._collect_pending_changes.run(
                PendingChangesRequest(
                    business=business,
                    version=version,
                    language=business.owner_language,
                )
            )
        )
