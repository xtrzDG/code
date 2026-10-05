"""
The retention engine: the window of records one purge reads, its result
for a business, and Settings → Privacy (the owner's retention choices and
what the last purge removed).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.privacy import SubProcessor
from app.schemas.domain.retention_purges import RetentionPurgeCounts
from app.schemas.typings.businesses.constrained_integers import (
    RecordingRetentionDays,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.privacy.constrained_integers import (
    ConversationRetentionDays,
    LlmTurnRetentionDays,
)
from app.schemas.typings.users.prefixed_id import UserId


class RetentionWindow(ImmutableDTO):
    """
    The records whose timestamp (a conversation's last message, a lead's
    creation, a visit's end) lies from `since` (inclusive; from the first
    record when None) to `before` (exclusive): what went past retention
    since the previous purge.
    """

    since: Microseconds | None = None
    before: Microseconds


class PrivacySettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class PrivacySettingsRequest(ImmutableDTO):
    """The owner's retention choices (Settings → Privacy)."""

    conversation_retention_days: ConversationRetentionDays
    llm_turn_retention_days: LlmTurnRetentionDays


class UpdatePrivacySettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: PrivacySettingsRequest
    client_ip_address: ClientIpAddress | None = None


class RetentionPurgeView(ImmutableDTO):
    """The latest run of the business's retention purge and what it removed."""

    ran_at: Microseconds
    counts: RetentionPurgeCounts


class PrivacySettingsView(ImmutableDTO):
    """
    Settings → Privacy: how long conversations and the records of model
    calls are kept, how long call recordings are kept (Settings → General),
    the latest purge, and the sub-processors whose copies are deleted with
    the platform's own (only those this platform is set up with).
    """

    conversation_retention_days: ConversationRetentionDays
    llm_turn_retention_days: LlmTurnRetentionDays
    recording_retention_days: RecordingRetentionDays
    last_purge: RetentionPurgeView | None = None
    erasure_processors: list[SubProcessor] = Field(default_factory=list[SubProcessor])
