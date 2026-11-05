from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AutotestCaseSource,
    AutotestCheckCode,
    AutotestExpectation,
    AutotestOutcome,
)
from app.schemas.typings.assistants.booleans import IsAutotestCaseActive
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestCaseId,
)
from app.schemas.typings.assistants.strings import JudgeNote
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class OwnerCheckSnapshot(PersistentDocument):
    """
    An owner check as an autotest run played it: its question and what the
    answer had to do, kept with the result so a later edit or removal of
    the check does not change what the run says it checked.
    """

    question: AutotestCaseQuestion
    expectation: AutotestExpectation
    expected_text: AutotestExpectedText | None = None


class OwnerCheckProbe(PersistentDocument):
    """
    "Check now": the check asked once of the version customers talk to
    (`assistant_version_id`) when it was saved, and how that went: the
    outcome, why it failed, the assistant's first answer, the semantic
    judge's notes and the test conversation the answer is in (so "Fix this
    answer" can open it). A passed probe newer than the check's last change
    counts as checked against that version.
    """

    assistant_version_id: AssistantVersionId
    outcome: AutotestOutcome
    check_codes: list[AutotestCheckCode] = Field(
        default_factory=list[AutotestCheckCode]
    )
    answer: MessageText | None = None
    judge_notes: list[JudgeNote] = Field(default_factory=list[JudgeNote])
    conversation_id: ConversationId | None = None
    answer_message_id: MessageId | None = None
    checked_at: Microseconds


class AutotestCaseDocument(BaseDocument):
    """
    One of the owner's own checks ("My checks"): a customer `question`
    asked word for word in `language`, and what the assistant's answer must
    do (`expectation`; MUST_MENTION and MUST_NOT_MENTION name their
    `expected_text`). Every autotest run of the business, the quick check
    of "Apply changes" included, plays its active checks, so a corrected
    answer stays correct.

    `source` says where it came from, with the record it was saved from: a
    corrected or rated answer (`source_conversation_id`,
    `source_message_id`) or a question the assistant could not answer
    (`source_question_id`). `created_by` is the person who saved it.
    `last_probe` is the latest "Check now" of the check, if any.
    """

    # 2: `last_probe` ("Check now"; optional, no upcaster).
    schema_version: SchemaVersion = SchemaVersion("2")
    id: AutotestCaseId = Field(default_factory=AutotestCaseId)
    business_id: BusinessId
    question: AutotestCaseQuestion
    expectation: AutotestExpectation
    expected_text: AutotestExpectedText | None = None
    language: LanguageTag
    source: AutotestCaseSource = AutotestCaseSource.OWNER
    source_conversation_id: ConversationId | None = None
    source_message_id: MessageId | None = None
    source_question_id: UnansweredQuestionId | None = None
    created_by: UserId | None = None
    is_active: IsAutotestCaseActive = True
    last_probe: OwnerCheckProbe | None = None
