from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.conversation_review_contracts import (
    ConversationReviewRepoContract,
)
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.knowledge import AnswerCorrectionScope
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.answer_corrections import (
    AnswerCorrectionRequest,
    AnswerCorrectionResult,
    CorrectAnswerCommand,
)
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.conversations.answer_fixes.answer_fix_items import (
    corrected_price_item,
    corrected_text_item,
    requested_target,
    to_fact_view,
)
from app.use_cases.conversations.answer_fixes.answer_messages import (
    find_question,
    load_answer,
)


class CorrectAnswerUseCase(
    UseCaseContract[CorrectAnswerCommand, AnswerCorrectionResult]
):
    """
    "Fix this answer" (owner only): the correction becomes knowledge the
    assistant answers from. A question, a rule or an hours line updates the
    item an earlier correction of the same answer made, the item the owner
    chose, or the item of the same kind and title, else it adds one; a
    price updates the chosen offer or adds one to the price list. The item
    is active, remembers the answer it corrected (`correction_of`) and,
    like every knowledge change, joins the changes customers do not get
    yet until the next "Apply changes". A bad rating of the conversation
    no longer waits for improvement.

    Raises:
        NotFoundError: the conversation, the answer or the chosen item is
            missing.
        ValidationFailedError: the message is not an answer of the
            assistant, or the correction lacks what its scope needs.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationRepoContract,
        conversation_review_repo: ConversationReviewRepoContract,
        message_repo: MessageRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        niche_template_registry: NicheTemplateRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._conversation_review_repo: ConversationReviewRepoContract = (
            conversation_review_repo
        )
        self._message_repo: MessageRepoContract = message_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._niche_template_registry: NicheTemplateRegistryContract = (
            niche_template_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CorrectAnswerCommand) -> AnswerCorrectionResult:
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
        language: LanguageTag = (
            conversation.language or answer.language or business.default_language
        )
        request: AnswerCorrectionRequest = self._with_question(
            input_data.request, business, answer
        )
        target: KnowledgeItemDocument | None = requested_target(
            self._knowledge_item_repo,
            business.id,
            request,
            self._knowledge_item_repo.find_by_correction(business.id, answer.id),
        )
        now: Microseconds = self._wall_clock.now_unix()
        item, is_new = (
            corrected_price_item(
                business,
                self._niche_template_registry.get(business.niche_key),
                request,
                target,
                language,
                now,
            )
            if request.scope is AnswerCorrectionScope.PRICE
            else corrected_text_item(
                business,
                request,
                target,
                self._knowledge_item_repo.list_by_business(business.id),
                language,
                now,
            )
        )
        item = item.model_copy(update={"correction_of": answer.id})
        self._knowledge_item_repo.save(item)
        self._conversation_review_repo.mark_improved(business.id, conversation.id, now)
        return AnswerCorrectionResult(
            conversation_id=conversation.id,
            message_id=answer.id,
            item=to_fact_view(item),
            is_new=is_new,
            question=request.question or item.title,
            language=language,
        )

    def _with_question(
        self,
        request: AnswerCorrectionRequest,
        business: BusinessDocument,
        answer: MessageDocument,
    ) -> AnswerCorrectionRequest:
        """
        A question, rule or hours line without a question of its own asks
        the customer's question before the answer (a price names its item).
        """

        if request.scope is AnswerCorrectionScope.PRICE or (
            request.question is not None and request.question.strip()
        ):
            return request

        question_message: MessageDocument | None = find_question(
            self._message_repo, business.id, answer
        )
        if question_message is None:
            return request

        return request.model_copy(
            update={"question": KnowledgeTitle(str(question_message.text).strip())}
        )
