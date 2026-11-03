"""
The phone assistant's call tools: decline_recording (a caller who will not
be recorded) and send_call_transcript (a caller who wants the call in
writing, ACC-03).
"""

import json
from collections.abc import Callable, Mapping

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolOutcome,
    DeclineRecordingToolInput,
    SendCallTranscriptToolInput,
)
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.use_cases.conversations.tools.tool_outcomes import (
    error_outcome,
    success_outcome,
)

DECLINED_NOTE: str = (
    "The call goes on without a recording: its audio is deleted after the "
    "call and only a transcript without phone, e-mail, card or account "
    "numbers is kept. Tell the caller so in one short sentence, in their "
    "language, and continue helping them."
)
TRANSCRIPT_TEXTED_NOTE: str = (
    "Say in one short sentence that the transcript of this call is texted "
    "to them right after the call ends, then continue helping them."
)
TRANSCRIPT_UNREACHABLE_NOTE: str = (
    "This caller cannot get a message from the business: do not promise "
    "one. Say they can write to the business in its website chat instead, "
    "or offer to pass the request to a colleague."
)


def run_decline_recording(
    call: LlmToolCall, context: AssistantToolContext
) -> AssistantToolOutcome:
    """
    Nothing changes during the call: the voice platform's report of the
    finished call names this tool, and the post-call flow deletes the
    call's audio and keeps a redacted transcript (`CallDocument.
    recording_declined`). A chat has no recording to decline.
    """

    if context.channel is not ChannelKind.PHONE:
        return error_outcome(call, "Only a phone call can be recorded.")

    DeclineRecordingToolInput.model_validate_json(call.input_json)
    return success_outcome(
        call,
        LlmToolResultJson(
            json.dumps(
                {"recording": "declined", "note": DECLINED_NOTE}, ensure_ascii=False
            )
        ),
    )


def run_send_call_transcript(
    call: LlmToolCall, context: AssistantToolContext
) -> AssistantToolOutcome:
    """
    Nothing is sent during the call: the voice platform's report of the
    finished call names this tool, and the post-call flow texts the caller
    the call's transcript on the first messenger that reaches them
    (`SendCallLinksUseCase`, with the links the call promised). Whether a
    messenger reaches the caller now decides what the agent may promise. A
    chat is already in writing.
    """

    if context.channel is not ChannelKind.PHONE:
        return error_outcome(call, "Only a phone call has a transcript to send.")

    SendCallTranscriptToolInput.model_validate_json(call.input_json)
    return success_outcome(
        call,
        LlmToolResultJson(
            json.dumps(
                {
                    "texted_after_call": bool(context.can_text_caller),
                    "note": TRANSCRIPT_TEXTED_NOTE
                    if context.can_text_caller
                    else TRANSCRIPT_UNREACHABLE_NOTE,
                },
                ensure_ascii=False,
            )
        ),
    )


CALL_TOOL_HANDLERS: Mapping[
    AssistantToolName,
    Callable[[LlmToolCall, AssistantToolContext], AssistantToolOutcome],
] = {
    AssistantToolName.DECLINE_RECORDING: run_decline_recording,
    AssistantToolName.SEND_CALL_TRANSCRIPT: run_send_call_transcript,
}
