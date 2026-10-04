"""
One evaluation conversation, played the way an autotest plays it: the AI
customer (a model with the persona prompt) writes, each message goes
through the real ConversationTurnOrchestrator as a sandbox owner-test
message pinned to the assembled version, and [DONE] ends it. The judge,
when the run has one, then scores the five autotest criteria.
"""

from dataclasses import dataclass, field

from app.containers.app import AppContainer
from app.contracts.llm import LlmAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AutotestTranscriptLine
from app.schemas.dto.assistants.autotest_runs import AutotestScenario, JudgeVerdict
from app.schemas.dto.conversations import (
    AssistantReply,
    InboundMessage,
    LlmRequest,
    LlmResponse,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmProviderPayload,
    MessageText,
)
from app.utilities.assembly.autotest_prompts import (
    CUSTOMER_OPENING_TEXT,
    JUDGE_SYSTEM_PROMPT,
    SILENT_ASSISTANT_TEXT,
    build_assistant_turn_text,
    build_judge_request_text,
    read_customer_message,
)
from app.utilities.assembly.judge_verdicts import parse_judge_verdict
from scripts.eval_harness.business_seeding import SeededBusiness
from scripts.eval_harness.call_metering import CallMeter


@dataclass
class Conversation:
    """What happened, filled as it goes so an error keeps what came before."""

    transcript: list[AutotestTranscriptLine] = field(
        default_factory=list[AutotestTranscriptLine]
    )
    replies: list[AssistantReply] = field(default_factory=list[AssistantReply])
    turn_latencies_ms: list[int] = field(default_factory=list[int])


def converse(
    container: AppContainer,
    seeded: SeededBusiness,
    scenario: AutotestScenario,
    persona_prompt: SystemPromptText,
    customer_model: LlmModelId,
    turn_limit: int,
    meter: CallMeter,
    conversation: Conversation,
) -> None:
    """Play the conversation into `conversation`; provider errors propagate."""

    llm: LlmAdapterContract = container.adapters.llm_adapter()
    settings: AppSettings = container.config.app_settings()
    orchestrator = (
        container.orchestrators.conversations.conversation_turn_orchestrator()
    )
    customer_transcript: list[LlmProviderPayload] = [
        llm.build_user_text_turn(MessageText(CUSTOMER_OPENING_TEXT))
    ]
    channel_user_id = ChannelUserId(f"eval-{scenario.key}")
    for _ in range(turn_limit):
        response: LlmResponse = llm.complete(
            LlmRequest(
                model_id=customer_model,
                system_prompt=persona_prompt,
                tools=[],
                transcript=list(customer_transcript),
                max_output_tokens=settings.llm_max_output_tokens,
                effort=settings.llm_judge_effort,
            )
        )
        customer_transcript.append(response.assistant_turn_payload)
        message: MessageText | None = read_customer_message(
            None if response.text is None else str(response.text)
        )
        if message is None:
            return

        conversation.transcript.append(
            AutotestTranscriptLine(author=MessageAuthor.CUSTOMER, text=message)
        )
        elapsed_before: int = meter.assistant_elapsed_ms
        reply: AssistantReply = orchestrator.execute(
            InboundMessage(
                business_id=seeded.business.id,
                channel=ChannelKind.OWNER_TEST,
                channel_user_id=channel_user_id,
                text=message,
                is_sandbox=True,
                assistant_version_id=seeded.version.id,
            )
        )
        conversation.turn_latencies_ms.append(
            meter.assistant_elapsed_ms - elapsed_before
        )
        conversation.replies.append(reply)
        conversation.transcript.append(
            AutotestTranscriptLine(author=MessageAuthor.ASSISTANT, text=reply.text)
            if reply.text is not None
            else AutotestTranscriptLine(
                author=MessageAuthor.SYSTEM, text=MessageText(SILENT_ASSISTANT_TEXT)
            )
        )
        customer_transcript.append(
            llm.build_user_text_turn(build_assistant_turn_text(reply))
        )


def judge_conversation(
    container: AppContainer,
    seeded: SeededBusiness,
    scenario: AutotestScenario,
    judge_model: LlmModelId,
    conversation: Conversation,
) -> JudgeVerdict | None:
    """The judge's verdict, or None when its answer cannot be read."""

    llm: LlmAdapterContract = container.adapters.llm_adapter()
    settings: AppSettings = container.config.app_settings()
    response: LlmResponse = llm.complete(
        LlmRequest(
            model_id=judge_model,
            system_prompt=SystemPromptText(JUDGE_SYSTEM_PROMPT),
            tools=[],
            transcript=[
                llm.build_user_text_turn(
                    build_judge_request_text(
                        scenario,
                        seeded.version.facts,
                        conversation.transcript,
                        conversation.replies,
                        seeded.business.owner_language,
                    )
                )
            ],
            max_output_tokens=settings.llm_max_output_tokens,
            effort=settings.llm_judge_effort,
        )
    )
    return parse_judge_verdict(None if response.text is None else str(response.text))
