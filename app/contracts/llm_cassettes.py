"""Seams of the evaluation harness's recorded model calls."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.llm_cassettes import (
    LlmCassetteEntry,
    LlmCassetteRecording,
    LlmCassetteRequest,
    LlmCassetteTake,
)
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.evaluations.constrained_strings import (
    LlmCassetteKey,
    LlmInstructionDigest,
    LlmToolsDigest,
)
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds


class LlmCassetteStoreAdapterContract(AdapterContract, Protocol):
    """
    Recorded model calls of one cassette, keyed by request. Reads are from
    memory; `save` writes what was recorded.
    """

    def recording(self) -> LlmCassetteRecording | None:
        """The models the cassette was recorded with; None when it is empty."""
        raise NotImplementedError

    def set_recording(self, recording: LlmCassetteRecording) -> None:
        raise NotImplementedError

    def find(self, key: LlmCassetteKey) -> LlmCassetteEntry | None:
        raise NotImplementedError

    def list_entries(self) -> list[LlmCassetteEntry]:
        """Every recorded request, to explain why a replayed one has none."""
        raise NotImplementedError

    def record(self, request: LlmCassetteRequest, take: LlmCassetteTake) -> None:
        """Store an answer; a take of the same sample replaces the older one."""
        raise NotImplementedError

    def remember_instruction(
        self, digest: LlmInstructionDigest, text: SystemPromptText
    ) -> None:
        raise NotImplementedError

    def read_instruction(self, digest: LlmInstructionDigest) -> SystemPromptText | None:
        raise NotImplementedError

    def remember_tools(
        self, digest: LlmToolsDigest, tool_names: list[AssistantToolName]
    ) -> None:
        raise NotImplementedError

    def read_tools(self, digest: LlmToolsDigest) -> list[AssistantToolName] | None:
        raise NotImplementedError

    def save(self) -> None:
        """Persist what was recorded (a file store writes its file)."""
        raise NotImplementedError


class LlmCallObserverContract(AdapterContract, Protocol):
    """Told about every answered model call (cost and latency of a run)."""

    def observe(
        self,
        request: LlmRequest,
        response: LlmResponse,
        elapsed: ElapsedMilliseconds,
    ) -> None:
        raise NotImplementedError
