"""
The teaching use cases over a brain world (tests/brain/brain_world.py):
real conversations answered by a scripted model, then "Fix this answer",
bad ratings with their reasons, "Answers worth improving" and the owner's
checks, all over in-memory repositories.
"""

from dataclasses import dataclass
from datetime import timedelta

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.repositories.assistant_repositories import AutotestRunRepository
from app.repositories.autotest_case_repository import AutotestCaseRepository
from app.repositories.booking_repositories import UnansweredQuestionRepository
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AutotestRunDocument
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.strings import UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.conversations.conversation_summary_transformer import (
    ConversationSummaryTransformer,
)
from app.use_cases.autotests.cases.create_autotest_case_use_case import (
    CreateAutotestCaseUseCase,
)
from app.use_cases.autotests.cases.delete_autotest_case_use_case import (
    DeleteAutotestCaseUseCase,
)
from app.use_cases.autotests.cases.list_autotest_cases_use_case import (
    ListAutotestCasesUseCase,
)
from app.use_cases.autotests.cases.update_autotest_case_use_case import (
    UpdateAutotestCaseUseCase,
)
from app.use_cases.conversations.answer_fixes.correct_answer_use_case import (
    CorrectAnswerUseCase,
)
from app.use_cases.conversations.answer_fixes.get_answer_correction_draft_use_case import (  # noqa: E501
    GetAnswerCorrectionDraftUseCase,
)
from app.use_cases.conversations.answer_fixes.list_answers_to_improve_use_case import (
    ListAnswersToImproveUseCase,
)
from app.use_cases.conversations.rate_conversation_use_case import (
    RateConversationUseCase,
)
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import scripted


@dataclass
class TeachingWorld:
    brain: BrainWorld
    question_repo: UnansweredQuestionRepository
    case_repo: AutotestCaseRepository
    run_repo: AutotestRunRepository
    draft: GetAnswerCorrectionDraftUseCase
    correct: CorrectAnswerUseCase
    rate: RateConversationUseCase
    improve: ListAnswersToImproveUseCase
    list_cases: ListAutotestCasesUseCase
    create_case: CreateAutotestCaseUseCase
    update_case: UpdateAutotestCaseUseCase
    delete_case: DeleteAutotestCaseUseCase

    def answer_of(self, reply: AssistantReply) -> MessageDocument:
        """The stored assistant message of a reply."""

        return [
            message
            for message in self.brain.messages(reply.conversation_id)
            if message.author is MessageAuthor.ASSISTANT
        ][-1]

    def messages(self, conversation_id: ConversationId) -> list[MessageDocument]:
        return self.brain.messages(conversation_id)

    def record_question(
        self, text: str, language: str = "ru", is_sandbox: bool = False
    ) -> UnansweredQuestionDocument:
        question = UnansweredQuestionDocument(
            business_id=self.brain.business.id,
            question=UnansweredQuestionText(text),
            language=LanguageTag(language),
            last_seen_at=self.brain.clock.wall_clock().now_unix(),
            is_sandbox=is_sandbox,
        )
        self.question_repo.save(question)
        return question

    def store_menu(self) -> list[KnowledgeItemDocument]:
        """The menu the scripted tools answer from, kept as knowledge items."""

        stored: list[KnowledgeItemDocument] = []
        for view in self.brain.get_price.items:
            item = KnowledgeItemDocument(
                id=view.id,
                business_id=self.brain.business.id,
                kind=view.kind,
                title=view.title,
                price_minor=view.price_minor,
                currency_code=view.currency_code,
            )
            self.brain.knowledge_item_repo.save(item)
            stored.append(item)

        return stored

    def advance(self, seconds: int) -> None:
        self.brain.clock.advance(timedelta(seconds=seconds))


def build_teaching_world(*turns: ScriptedLlmTurn) -> TeachingWorld:
    """A brain world whose model plays `turns`, with the teaching use cases."""

    brain = build_world(scripted(*turns))
    question_repo = UnansweredQuestionRepository(
        InMemoryDocumentCollectionAdapter(UnansweredQuestionDocument)
    )
    case_repo = AutotestCaseRepository(
        InMemoryDocumentCollectionAdapter(AutotestCaseDocument)
    )
    run_repo = AutotestRunRepository(
        InMemoryDocumentCollectionAdapter(AutotestRunDocument)
    )
    wall_clock = brain.clock.wall_clock()
    return TeachingWorld(
        brain=brain,
        question_repo=question_repo,
        case_repo=case_repo,
        run_repo=run_repo,
        draft=GetAnswerCorrectionDraftUseCase(
            authorize_business_access=brain.authorize,
            conversation_repo=brain.conversation_repo,
            message_repo=brain.message_repo,
            knowledge_item_repo=brain.knowledge_item_repo,
            audit_log_repo=brain.audit_log_repo,
            wall_clock=wall_clock,
        ),
        correct=CorrectAnswerUseCase(
            authorize_business_access=brain.authorize,
            conversation_repo=brain.conversation_repo,
            conversation_review_repo=brain.conversation_repo,
            message_repo=brain.message_repo,
            knowledge_item_repo=brain.knowledge_item_repo,
            niche_template_registry=NicheTemplateRegistry(),
            wall_clock=wall_clock,
        ),
        rate=RateConversationUseCase(
            authorize_business_access=brain.authorize,
            conversation_repo=brain.conversation_repo,
            conversation_review_repo=brain.conversation_repo,
            contact_repo=brain.contact_repo,
            message_repo=brain.message_repo,
            summary_transformer=ConversationSummaryTransformer(),
            wall_clock=wall_clock,
        ),
        improve=ListAnswersToImproveUseCase(
            authorize_business_access=brain.authorize,
            conversation_review_repo=brain.conversation_repo,
            message_repo=brain.message_repo,
            unanswered_question_repo=question_repo,
        ),
        list_cases=ListAutotestCasesUseCase(
            authorize_business_access=brain.authorize,
            autotest_case_repo=case_repo,
            assistant_version_repo=brain.version_repo,
            autotest_run_repo=run_repo,
        ),
        create_case=CreateAutotestCaseUseCase(
            authorize_business_access=brain.authorize,
            autotest_case_repo=case_repo,
            conversation_repo=brain.conversation_repo,
            conversation_review_repo=brain.conversation_repo,
            message_repo=brain.message_repo,
            unanswered_question_repo=question_repo,
            wall_clock=wall_clock,
        ),
        update_case=UpdateAutotestCaseUseCase(
            authorize_business_access=brain.authorize,
            autotest_case_repo=case_repo,
            wall_clock=wall_clock,
        ),
        delete_case=DeleteAutotestCaseUseCase(
            authorize_business_access=brain.authorize,
            autotest_case_repo=case_repo,
        ),
    )
