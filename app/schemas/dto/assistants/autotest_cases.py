"""The owner's own checks ("My checks"): their API bodies and views."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AutotestCaseSource,
    AutotestCheckCode,
    AutotestExpectation,
    AutotestOutcome,
)
from app.schemas.typings.assistants.booleans import IsAutotestCaseActive
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
    AutotestCaseLimit,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId, AutotestRunId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class AutotestCaseInput(ImmutableDTO):
    """
    HTTP body of a new check. MUST_MENTION and MUST_NOT_MENTION need their
    `expected_text`; the language is the business's default one unless
    given. A check saved from a corrected or rated answer names its
    conversation and message; one saved from a question without an answer
    names the question.
    """

    question: AutotestCaseQuestion
    expectation: AutotestExpectation
    expected_text: AutotestExpectedText | None = None
    language: LanguageTag | None = None
    source: AutotestCaseSource = AutotestCaseSource.OWNER
    source_conversation_id: ConversationId | None = None
    source_message_id: MessageId | None = None
    source_question_id: UnansweredQuestionId | None = None


class AutotestCaseChanges(ImmutableDTO):
    """HTTP body of a change to a check; missing fields stay as they are."""

    question: AutotestCaseQuestion | None = None
    expectation: AutotestExpectation | None = None
    expected_text: AutotestExpectedText | None = None
    language: LanguageTag | None = None
    is_active: IsAutotestCaseActive | None = None


class ListAutotestCasesQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class CreateAutotestCaseCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    case: AutotestCaseInput


class UpdateAutotestCaseCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    case_id: AutotestCaseId
    changes: AutotestCaseChanges


class AutotestCaseCommand(ImmutableDTO):
    """One check of a business (its removal)."""

    user_id: UserId
    business_id: BusinessId
    case_id: AutotestCaseId


class AutotestCaseResultView(ImmutableDTO):
    """
    How the check did in the latest finished autotest run that played it:
    the outcome, why it failed, the assistant's first answer and when.
    """

    run_id: AutotestRunId
    assistant_version_number: AssistantVersionNumber
    outcome: AutotestOutcome
    check_codes: list[AutotestCheckCode] = Field(
        default_factory=list[AutotestCheckCode]
    )
    answer: MessageText | None = None
    checked_at: Microseconds


class AutotestCaseView(ImmutableDTO):
    """A check as "My checks" lists it, with its latest result (None: not run yet)."""

    id: AutotestCaseId
    question: AutotestCaseQuestion
    expectation: AutotestExpectation
    expected_text: AutotestExpectedText | None = None
    language: LanguageTag
    source: AutotestCaseSource
    source_conversation_id: ConversationId | None = None
    is_active: IsAutotestCaseActive
    created_at: Microseconds
    last_result: AutotestCaseResultView | None = None


class AutotestCaseList(ImmutableDTO):
    """The business's checks, the first written first, and how many it may keep."""

    items: list[AutotestCaseView] = Field(default_factory=list[AutotestCaseView])
    limit: AutotestCaseLimit
