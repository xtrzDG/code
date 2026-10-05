from base_pydantic_schemas import BaseDocument, SchemaVersion

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.booleans import IsQualitySamplingAllowed
from app.schemas.typings.privacy.constrained_integers import (
    ConversationRetentionDays,
    LlmTurnRetentionDays,
)
from app.schemas.typings.privacy.prefixed_id import BusinessPrivacySettingsId

DEFAULT_CONVERSATION_RETENTION_DAYS: ConversationRetentionDays = (
    ConversationRetentionDays(730)
)
DEFAULT_LLM_TURN_RETENTION_DAYS: LlmTurnRetentionDays = LlmTurnRetentionDays(30)


class BusinessPrivacySettingsDocument(BaseDocument):
    """
    How long one business keeps its customers' data (Settings → Privacy);
    one document per business, the id derived from it. A business without
    one keeps the defaults.

    `conversation_retention_days`: a conversation quiet that long loses its
    messages, the team's notes and its call transcripts and recordings,
    and the leads, bookings (once the visit is over) and handoffs it
    produced keep only what is not personal, as an erasure leaves them.
    `llm_turn_retention_days`: a conversation quiet that long loses the
    verbatim records of its model calls, here and at the quality journal.
    A conversation stays open only while messages keep coming within a
    day, so no open conversation loses its model records.
    `quality_sampling_allowed`: the nightly judge may score a sample of the
    business's real conversations (production quality); off, none of them
    is ever sent to the judge.
    """

    # 2: `quality_sampling_allowed` (optional with its default, so version 1
    # needs no upcaster).
    schema_version: SchemaVersion = SchemaVersion("2")
    id: BusinessPrivacySettingsId
    business_id: BusinessId
    conversation_retention_days: ConversationRetentionDays = (
        DEFAULT_CONVERSATION_RETENTION_DAYS
    )
    llm_turn_retention_days: LlmTurnRetentionDays = DEFAULT_LLM_TURN_RETENTION_DAYS
    quality_sampling_allowed: IsQualitySamplingAllowed = True
