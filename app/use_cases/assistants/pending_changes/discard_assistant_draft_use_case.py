from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.setup_repositories import AssistantApplyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.setup import AssistantApplyDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.pending_changes import DiscardDraftCommand
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.assistants.apply.apply_records import is_apply_running
from app.utilities.assembly.version_retirement import is_pending_draft

DRAFT_AUDIT_ENTITY: AuditEntityName = AuditEntityName("assistant_version")


class DiscardAssistantDraftUseCase(UseCaseContract[DiscardDraftCommand, None]):
    """
    The owner discards a draft from the "Apply changes" sheet: a version
    built after the live one that customers never got (see
    `is_pending_draft`). It leaves the drafts and the history but stays
    readable, as versions discarded at a go-live do, and the test chat
    stops choosing it. The check and the write are one step, so a draft
    that a moment ago started its checks or went live is not discarded;
    neither is the version an apply is working on. Written to the audit
    log; the business's open cabinets read their changes again.

    Raises:
        NotFoundError: no such version of this business.
        ConflictError: the version is live, archived, under test, already
            discarded, older than the live one, or an apply is working on
            it.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        assistant_apply_repo: AssistantApplyRepoContract,
        audit_log_repo: AuditLogRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._assistant_apply_repo: AssistantApplyRepoContract = assistant_apply_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DiscardDraftCommand) -> None:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                # Done-for-you setup: support may, with the owner's consent.
                support_may_change=True,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        versions: list[AssistantVersionDocument] = (
            self._assistant_version_repo.list_by_business(business.id)
        )
        if not any(
            version.id == input_data.assistant_version_id for version in versions
        ):
            raise NotFoundError(
                f"Assistant version {input_data.assistant_version_id} was not found."
            )

        apply: AssistantApplyDocument | None = (
            self._assistant_apply_repo.get_by_business(business.id)
        )
        if (
            apply is not None
            and apply.assistant_version_id == input_data.assistant_version_id
            and is_apply_running(apply, versions, now)
        ):
            raise ConflictError(
                "This version is being checked for customers; wait for the "
                "update to finish."
            )

        live: AssistantVersionDocument | None = next(
            (
                version
                for version in versions
                if version.id == business.published_assistant_version_id
            ),
            None,
        )

        def discard(
            stored: AssistantVersionDocument,
        ) -> AssistantVersionDocument | None:
            if not is_pending_draft(stored, live):
                return None

            stored.discarded_at = now
            stored.updated_at = now
            return stored

        discarded: AssistantVersionDocument | None = (
            self._assistant_version_repo.modify(
                business.id, input_data.assistant_version_id, discard
            )
        )
        if discarded is None:
            raise ConflictError(
                "Only a version customers never got can be discarded, and not "
                "while its checks run."
            )

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.DELETE,
                entity=DRAFT_AUDIT_ENTITY,
                entity_id=AuditEntityReference(str(discarded.id)),
                created_at=now,
                updated_at=now,
            )
        )
        self._live_events.publish(
            business.id, LiveEventKind.ASSISTANT_APPLY, (discarded.id,)
        )
