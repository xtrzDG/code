from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field

from app.schemas.constants.assistants import AutotestCaseSource, AutotestExpectation
from app.schemas.typings.assistants.booleans import IsAutotestCaseActive
from app.schemas.typings.assistants.constrained_strings import (
    AutotestCaseQuestion,
    AutotestExpectedText,
)
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.handoffs.prefixed_id import UnansweredQuestionId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


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
    """

    schema_version: SchemaVersion = SchemaVersion("1")
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
