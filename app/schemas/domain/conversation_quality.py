from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import JudgeCriterionScore
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import JudgeNote
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.quality.constrained_integers import (
    ConversationQualityHundredths,
)
from app.schemas.typings.quality.prefixed_id import ConversationQualityScoreId


class ConversationQualityScoreDocument(BaseDocument):
    """
    The judge's score of one real conversation (production quality, the
    nightly sample of QUALITY_SAMPLE_PERCENT of the day's conversations).

    The same five criteria as the autotests, scored by the judge model
    (LLM_JUDGE_MODEL_ID) on the conversation's transcript with phone
    numbers and e-mail addresses blanked out; `score_hundredths` is their
    average (4.6 of 5 is 460), so the database sums a business's scores
    per day. The judge's notes are in the owner's language and describe
    problems without quoting the customer. One score per conversation (the
    id derives from it); kept 90 days.
    """

    id: ConversationQualityScoreId
    business_id: BusinessId
    conversation_id: ConversationId
    assistant_version_id: AssistantVersionId
    channel: ChannelKind
    language: LanguageTag | None = None
    scores: list[JudgeCriterionScore]
    score_hundredths: ConversationQualityHundredths
    judge_notes: list[JudgeNote] = Field(default_factory=list[JudgeNote])
    judge_model_id: LlmModelId
    cost_micro_usd: CostMicroUsd
    judged_at: Microseconds
