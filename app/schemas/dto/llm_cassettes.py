"""
Recorded model calls ("cassettes") of the evaluation harness: a recording
adapter stores what a model answered to each request, and a replay adapter
answers the same requests from the recording without any provider.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.conversations import LlmResponse
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.evaluations.constrained_integers import (
    LlmCassetteFormatVersion,
    LlmCassetteSampleIndex,
)
from app.schemas.typings.evaluations.constrained_strings import (
    LlmInstructionDigest,
    LlmRequestDigest,
    LlmToolsDigest,
    LlmTranscriptDigest,
)
from app.schemas.typings.evaluations.strings import (
    LlmCassetteMissReason,
    LlmTranscriptTail,
)
from app.schemas.typings.platform.constrained_integers import ElapsedMilliseconds


class LlmCassetteRequest(ImmutableDTO):
    """
    What identifies a model call: the model and the digests of its
    instruction, tools and canonical transcript; `request_digest` hashes
    all four and keys the recording.
    """

    request_digest: LlmRequestDigest
    model_id: LlmModelId
    instruction_digest: LlmInstructionDigest
    tools_digest: LlmToolsDigest
    transcript_digest: LlmTranscriptDigest
    transcript_tail: LlmTranscriptTail


class LlmCassetteTake(ImmutableDTO):
    """One recorded answer to a request, in one sample of its scenario."""

    sample_index: LlmCassetteSampleIndex
    response: LlmResponse
    elapsed: ElapsedMilliseconds


class LlmCassetteEntry(ImmutableDTO):
    """A request and every answer recorded for it (one per sample)."""

    request: LlmCassetteRequest
    takes: list[LlmCassetteTake] = Field(default_factory=list[LlmCassetteTake])


class LlmCassetteRecording(ImmutableDTO):
    """The models a cassette was recorded with; replay uses the same ids."""

    assistant_model_id: LlmModelId
    customer_model_id: LlmModelId
    judge_model_id: LlmModelId | None = None


class LlmCassetteInstruction(ImmutableDTO):
    """A system prompt seen while recording, kept to diff a later change."""

    digest: LlmInstructionDigest
    text: SystemPromptText


class LlmCassetteToolSet(ImmutableDTO):
    """The tool names behind a tools digest, kept to name a later change."""

    digest: LlmToolsDigest
    tool_names: list[AssistantToolName]


class LlmCassetteMiss(ImmutableDTO):
    """A replayed call without a recording, and why."""

    request: LlmCassetteRequest
    sample_index: LlmCassetteSampleIndex
    reason: LlmCassetteMissReason


class LlmCassetteFile(ImmutableDTO):
    """
    One cassette as stored: the models it was recorded with, the
    instructions and tool sets it saw, and every recorded request, each
    list in a stable order so a re-recording diffs cleanly.
    """

    format_version: LlmCassetteFormatVersion
    recording: LlmCassetteRecording | None = None
    instructions: list[LlmCassetteInstruction] = Field(
        default_factory=list[LlmCassetteInstruction]
    )
    tool_sets: list[LlmCassetteToolSet] = Field(
        default_factory=list[LlmCassetteToolSet]
    )
    entries: list[LlmCassetteEntry] = Field(default_factory=list[LlmCassetteEntry])
