from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName, LlmEffort
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import LlmStopReason
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.observability.constrained_strings import TraceId
from app.schemas.typings.platform.constrained_integers import (
    ElapsedMilliseconds,
    JobIntervalSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName, RequestId
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import (
    CorrelationId,
    JobCheckInId,
    JobErrorText,
)


class LlmGenerationTrace(ImmutableDTO):
    """
    One language-model call as written to the quality journal (Langfuse).

    Texts are present only when content tracing is enabled; by default the
    journal keeps metadata only, because conversations hold personal data.
    The business, contact and conversation the call answered (from the log
    context) tag the trace, so its copies can be found and deleted with
    theirs. The request id and the distributed trace id of the work that
    made the call (the webhook and its job) join it to logs and spans.
    """

    trace_id: CorrelationId
    model_id: LlmModelId
    effort: LlmEffort
    offered_tools: list[AssistantToolName] = Field(
        default_factory=list[AssistantToolName]
    )
    called_tools: list[AssistantToolName] = Field(
        default_factory=list[AssistantToolName]
    )
    stop_reason: LlmStopReason | None = None
    input_tokens: LlmTokenCount = LlmTokenCount(0)
    output_tokens: LlmTokenCount = LlmTokenCount(0)
    started_at: Microseconds
    elapsed: ElapsedMilliseconds
    input_text: MessageText | None = None
    output_text: MessageText | None = None
    error: JobErrorText | None = None
    business_id: BusinessId | None = None
    contact_id: ContactId | None = None
    conversation_id: ConversationId | None = None
    request_id: RequestId | None = None
    request_trace_id: TraceId | None = None


class LogContext(ImmutableDTO):
    """
    What one log line, error report or trace was about: the HTTP request
    and its distributed trace, the business, the conversation and its
    channel, the background job. Ids and names only, never texts or
    contact data.
    """

    request_id: RequestId | None = None
    trace_id: TraceId | None = None
    business_id: BusinessId | None = None
    conversation_id: ConversationId | None = None
    contact_id: ContactId | None = None
    channel: ChannelKind | None = None
    job_name: JobName | None = None
    job_id: QueuedJobId | None = None

    def as_fields(self) -> dict[str, str]:
        """The values that are set, by field name (for log lines and tags)."""

        return {
            name: str(value)
            for name, value in self.model_dump(mode="json").items()
            if value is not None
        }


class JobCheckIn(ImmutableDTO):
    """A periodic job run the job monitor (Sentry Crons) was told about."""

    job_name: JobName
    interval_seconds: JobIntervalSeconds
    check_in_id: JobCheckInId | None = None
