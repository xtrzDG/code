from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument, ToolCallRecord
from app.schemas.dto.assistant_tools import AssistantToolContext, AssistantToolOutcome
from app.schemas.dto.conversation_engine import VoiceToolCallRecord
from app.schemas.dto.conversations import VoiceToolCallResult
from app.schemas.typings.conversations.strings import MessageText


class RecordVoiceToolCallUseCase(
    UseCaseContract[VoiceToolCallRecord, VoiceToolCallResult]
):
    """
    Keep a voice-agent tool call in the conversation feed (a system message
    with the tool call record) and return its result to the agent. The call
    transcript itself arrives after the call from the voice platform.
    """

    def __init__(
        self,
        message_repo: MessageRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._message_repo: MessageRepoContract = message_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: VoiceToolCallRecord) -> VoiceToolCallResult:
        context: AssistantToolContext = input_data.context
        outcome: AssistantToolOutcome = input_data.outcome
        now: Microseconds = self._wall_clock.now_unix()
        self._message_repo.save(
            MessageDocument(
                conversation_id=context.conversation_id,
                business_id=context.business_id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.SYSTEM,
                text=MessageText(f"Voice agent called {outcome.tool_name}."),
                language=context.language,
                tool_calls=[
                    ToolCallRecord(
                        tool_name=outcome.tool_name,
                        input_json=input_data.call.input_json,
                        result_json=outcome.result.result_json,
                        is_error=outcome.result.is_error,
                    )
                ],
                created_at=now,
                updated_at=now,
            )
        )
        return VoiceToolCallResult(
            result_json=outcome.result.result_json,
            is_error=outcome.result.is_error,
        )
