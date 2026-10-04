from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.knowledge import AnswerCorrectionScope
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.answer_corrections import (
    AnswerCorrectionDraft,
    AnswerCorrectionQuery,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.use_cases.conversations.answer_fixes.answer_fix_items import (
    find_current_fact,
    to_fact_view,
)
from app.use_cases.conversations.answer_fixes.answer_messages import (
    find_question,
    load_answer,
)
from app.utilities.conversations.answer_fix_hints import suggest_scope

MESSAGE_ENTITY: AuditEntityName = AuditEntityName("message")


class GetAnswerCorrectionDraftUseCase(
    UseCaseContract[AnswerCorrectionQuery, AnswerCorrectionDraft]
):
    """
    "Fix this answer" opens (owner only): the customer's question before the
    assistant's answer, the kind of correction the answer suggests (a price
    it looked up or could not back, free time it checked, a policy claim
    the guard doubted, else a question), and the fact the dialog starts
    from (the item an earlier correction of the answer made, the item the
    assistant looked up, or the item the question names). Reading the
    customer's words is audited like the conversation card.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AnswerCorrectionQuery) -> AnswerCorrectionDraft:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        conversation, answer = load_answer(
            self._conversation_repo,
            self._message_repo,
            business.id,
            input_data.conversation_id,
            input_data.message_id,
        )
        question_message = find_question(self._message_repo, business.id, answer)
        question: KnowledgeTitle | None = (
            None
            if question_message is None
            else KnowledgeTitle(str(question_message.text).strip())
        )
        scope: AnswerCorrectionScope = suggest_scope(answer)
        fact: KnowledgeItemDocument | None = find_current_fact(
            self._knowledge_item_repo,
            business.id,
            answer,
            None if question is None else str(question),
            scope,
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=MESSAGE_ENTITY,
                entity_id=AuditEntityReference(str(answer.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return AnswerCorrectionDraft(
            conversation_id=conversation.id,
            message_id=answer.id,
            question=question,
            answer=answer.text,
            language=conversation.language or answer.language,
            suggested_scope=scope,
            current_fact=None if fact is None else to_fact_view(fact),
            is_corrected=fact is not None and fact.correction_of == answer.id,
            guard_reasons=list(answer.guard_reasons),
        )
