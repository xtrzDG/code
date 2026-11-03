from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import (
    DeleteKnowledgeItemCommand,
    KnowledgeItemDeletion,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.knowledge.knowledge_audit import audit_knowledge_change
from app.use_cases.shared.knowledge_index_queue import queue_knowledge_index


class DeleteKnowledgeItemUseCase(
    UseCaseContract[DeleteKnowledgeItemCommand, KnowledgeItemDeletion]
):
    """
    Delete a knowledge item of the business; a foreign item is reported
    missing. The business's knowledge is queued for indexing again (its
    vector is forgotten), and the deletion is audited with the team member
    who made it.
    """

    def __init__(
        self,
        knowledge_item_repo: KnowledgeItemRepoContract,
        job_queue: JobQueueFacilitatorContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DeleteKnowledgeItemCommand) -> KnowledgeItemDeletion:
        existing: KnowledgeItemDocument | None = self._knowledge_item_repo.get(
            input_data.business_id,
            input_data.item_id,
        )
        if existing is None:
            raise NotFoundError(f"Knowledge item {input_data.item_id} was not found.")

        self._knowledge_item_repo.delete(input_data.business_id, input_data.item_id)
        queue_knowledge_index(self._job_queue, input_data.business_id)
        audit_knowledge_change(
            self._audit_log_repo,
            input_data.business_id,
            existing.id,
            AuditAction.DELETE,
            input_data.user_id,
            self._wall_clock.now_unix(),
        )
        return KnowledgeItemDeletion(id=existing.id)
