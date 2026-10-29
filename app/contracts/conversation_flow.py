"""Cross-slice entry points into the conversation engine."""

from typing import Protocol

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.schemas.dto.conversations import (
    AssistantReply,
    InboundMessage,
    VoiceToolCallRequest,
    VoiceToolCallResult,
)


class ConversationTurnOrchestratorContract(
    OrchestratorContract[InboundMessage, AssistantReply],
    Protocol,
):
    """Answer one customer message (used by autotests with sandbox messages)."""


class CustomerMessagePipelineContract(
    PipelineContract[InboundMessage, AssistantReply],
    Protocol,
):
    """Full customer-message phase used by every channel gateway."""


class VoiceToolCallOrchestratorContract(
    OrchestratorContract[VoiceToolCallRequest, VoiceToolCallResult],
    Protocol,
):
    """Run one voice-agent tool call with the same tools the chat uses."""
