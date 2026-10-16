"""
Why a replayed model call has no recording, in words a developer can act
on: which part of the request changed since the cassette was recorded,
with a diff of the instruction, the tool names that came or went, or the
turn where the conversation took another path.
"""

import difflib
from collections.abc import Callable, Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.llm_cassettes import LlmCassetteEntry, LlmCassetteRequest
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.evaluations.constrained_strings import (
    LlmInstructionDigest,
    LlmToolsDigest,
)
from app.schemas.typings.evaluations.strings import LlmCassetteMissReason

MAX_DIFF_LINES: int = 60
DIFF_CONTEXT_LINES: int = 1

type InstructionReader = Callable[[LlmInstructionDigest], SystemPromptText | None]
type ToolsReader = Callable[[LlmToolsDigest], list[AssistantToolName] | None]


def explain_cassette_miss(
    request: LlmCassetteRequest,
    instruction: SystemPromptText,
    tool_names: Sequence[AssistantToolName],
    entries: Sequence[LlmCassetteEntry],
    read_instruction: InstructionReader,
    read_tools: ToolsReader,
) -> LlmCassetteMissReason:
    """
    The first difference that explains the miss, checked from the most to
    the least specific: only the instruction changed, only the tools
    changed, only the model changed, or the transcript differs from every
    recording of this instruction and tools.
    """

    def is_same(entry: LlmCassetteEntry, *, model: bool, text: bool) -> bool:
        recorded: LlmCassetteRequest = entry.request
        return (recorded.model_id == request.model_id) is model and (
            recorded.instruction_digest == request.instruction_digest
        ) is text

    for entry in entries:
        recorded = entry.request
        if (
            recorded.transcript_digest == request.transcript_digest
            and recorded.tools_digest == request.tools_digest
            and is_same(entry, model=True, text=False)
        ):
            return explain_instruction_change(
                read_instruction(recorded.instruction_digest), instruction
            )

    for entry in entries:
        recorded = entry.request
        if (
            recorded.transcript_digest == request.transcript_digest
            and recorded.tools_digest != request.tools_digest
            and is_same(entry, model=True, text=True)
        ):
            return explain_tools_change(read_tools(recorded.tools_digest), tool_names)

    for entry in entries:
        recorded = entry.request
        if (
            recorded.transcript_digest == request.transcript_digest
            and recorded.tools_digest == request.tools_digest
            and is_same(entry, model=False, text=True)
        ):
            return LlmCassetteMissReason(
                f"The cassette was recorded with model {recorded.model_id}; this "
                f"run asks {request.model_id}."
            )

    return explain_other_path(request, entries)


def explain_instruction_change(
    recorded: SystemPromptText | None,
    current: SystemPromptText,
) -> LlmCassetteMissReason:
    """The instruction changed: a unified diff of what the model reads."""

    if recorded is None:
        return LlmCassetteMissReason(
            "The instruction changed since the recording (its old text was not kept)."
        )

    diff_lines: list[str] = list(
        difflib.unified_diff(
            str(recorded).splitlines(),
            str(current).splitlines(),
            fromfile="recorded instruction",
            tofile="instruction now",
            n=DIFF_CONTEXT_LINES,
            lineterm="",
        )
    )
    shown: list[str] = diff_lines[:MAX_DIFF_LINES]
    if len(diff_lines) > MAX_DIFF_LINES:
        shown.append(f"... {len(diff_lines) - MAX_DIFF_LINES} more diff lines")

    return LlmCassetteMissReason(
        "The instruction changed since the recording:\n" + "\n".join(shown)
    )


def explain_tools_change(
    recorded: Sequence[AssistantToolName] | None,
    current: Sequence[AssistantToolName],
) -> LlmCassetteMissReason:
    """The tools changed: which came, which went, or that only schemas did."""

    if recorded is None:
        return LlmCassetteMissReason(
            "The tool definitions changed since the recording."
        )

    added: list[str] = [str(name) for name in current if name not in recorded]
    removed: list[str] = [str(name) for name in recorded if name not in current]
    if not added and not removed:
        return LlmCassetteMissReason(
            "The descriptions or input schemas of the tools changed since the "
            "recording (the same tools are offered)."
        )

    parts: list[str] = []
    if added:
        parts.append(f"added {', '.join(added)}")

    if removed:
        parts.append(f"removed {', '.join(removed)}")

    return LlmCassetteMissReason(
        f"The offered tools changed since the recording: {'; '.join(parts)}."
    )


def explain_other_path(
    request: LlmCassetteRequest,
    entries: Sequence[LlmCassetteEntry],
) -> LlmCassetteMissReason:
    """
    The conversation went another way: the request's last turn next to the
    most similar recorded one of the same instruction and tools.
    """

    candidates: list[LlmCassetteEntry] = [
        entry
        for entry in entries
        if entry.request.instruction_digest == request.instruction_digest
        and entry.request.tools_digest == request.tools_digest
        and entry.request.model_id == request.model_id
    ]
    if not candidates:
        return LlmCassetteMissReason(
            f"No call with this instruction and these tools was recorded for "
            f"model {request.model_id}: the scenario is new or its cassette was "
            "recorded for other data."
        )

    closest: LlmCassetteEntry = max(
        candidates,
        key=lambda entry: difflib.SequenceMatcher(
            None,
            str(entry.request.transcript_tail),
            str(request.transcript_tail),
        ).ratio(),
    )
    return LlmCassetteMissReason(
        "The conversation took another path than the recording (a tool result, "
        "a reply or a customer message changed).\n"
        f"Last turn now:      {request.transcript_tail}\n"
        f"Closest recorded:   {closest.request.transcript_tail}"
    )
