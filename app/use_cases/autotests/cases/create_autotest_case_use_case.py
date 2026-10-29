from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LanguageDetectorContract
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
)
from app.contracts.repositories.booking_repositories import (
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.conversation_review_contracts import (
    ConversationReviewRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.autotest_cases import AutotestCaseDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseInput,
    AutotestCaseView,
    CreateAutotestCaseCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.autotests.cases.autotest_case_rules import (
    check_expected_text,
    check_room,
    check_unique,
)
from app.use_cases.autotests.cases.autotest_case_views import to_case_view


class CreateAutotestCaseUseCase(
    UseCaseContract[CreateAutotestCaseCommand, AutotestCaseView]
):
    """
    "Save as a check" (owner only): a question and what the answer must do,
    written by hand or saved from a corrected answer, a bad rating or a
    question the assistant could not answer. From the next autotest run on
    (the quick check of "Apply changes" included) every version must pass
    it. A check saved from a conversation rated bad means someone acted on
    the rating, so it no longer waits in "Answers worth improving". Its
    language is the one asked for, else the one its question is written in
    (`detect_any`, the business's default language when the question tells
    too little).

    Raises:
        NotFoundError: the conversation, message or question it was saved
            from is not this business's.
        ValidationFailedError: a text expectation without its text, or the
            business keeps as many checks as it may.
        ConflictError: the same check exists.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        autotest_case_repo: AutotestCaseRepoContract,
        conversation_repo: ConversationRepoContract,
        conversation_review_repo: ConversationReviewRepoContract,
        message_repo: MessageRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        language_detector: LanguageDetectorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._conversation_review_repo: ConversationReviewRepoContract = (
            conversation_review_repo
        )
        self._message_repo: MessageRepoContract = message_repo
        self._unanswered_question_repo: UnansweredQuestionRepoContract = (
            unanswered_question_repo
        )
        self._language_detector: LanguageDetectorContract = language_detector
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateAutotestCaseCommand) -> AutotestCaseView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        case_input: AutotestCaseInput = input_data.case
        self._check_sources(business, case_input)
        expected_text = check_expected_text(
            case_input.expectation, case_input.expected_text
        )
        cases: list[AutotestCaseDocument] = self._autotest_case_repo.list_by_business(
            business.id
        )
        check_room(cases)
        check_unique(cases, case_input.question, case_input.expectation, expected_text)
        now: Microseconds = self._wall_clock.now_unix()
        case = AutotestCaseDocument(
            business_id=business.id,
            question=case_input.question,
            expectation=case_input.expectation,
            expected_text=expected_text,
            language=case_input.language
            or self._question_language(business, case_input),
            source=case_input.source,
            source_conversation_id=case_input.source_conversation_id,
            source_message_id=case_input.source_message_id,
            source_question_id=case_input.source_question_id,
            created_by=input_data.user_id,
            created_at=now,
            updated_at=now,
        )
        self._autotest_case_repo.save(case)
        if case.source_conversation_id is not None:
            self._conversation_review_repo.mark_improved(
                business.id, case.source_conversation_id, now
            )

        return to_case_view(case)

    def _question_language(
        self, business: BusinessDocument, case_input: AutotestCaseInput
    ) -> LanguageTag:
        """The language the question is written in, as a customer's would be."""

        return self._language_detector.detect_any(
            MessageText(str(case_input.question)),
            list(business.languages),
            business.default_language,
            None,
            None,
        ).language

    def _check_sources(
        self, business: BusinessDocument, case_input: AutotestCaseInput
    ) -> None:
        """The conversation, message and question named are this business's."""

        if case_input.source_conversation_id is not None:
            conversation: ConversationDocument | None = self._conversation_repo.get(
                business.id, case_input.source_conversation_id
            )
            if conversation is None:
                raise NotFoundError(
                    f"Conversation {case_input.source_conversation_id} was not found."
                )

        if case_input.source_message_id is not None:
            message: MessageDocument | None = self._message_repo.get(
                business.id, case_input.source_message_id
            )
            if message is None or (
                case_input.source_conversation_id is not None
                and message.conversation_id != case_input.source_conversation_id
            ):
                raise NotFoundError(
                    f"Message {case_input.source_message_id} was not found."
                )

        if (
            case_input.source_question_id is not None
            and self._unanswered_question_repo.get(
                business.id, case_input.source_question_id
            )
            is None
        ):
            raise NotFoundError(
                f"Question {case_input.source_question_id} was not found."
            )
