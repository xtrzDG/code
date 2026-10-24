"""The phone assistant's decline_recording tool: a caller who will not be recorded."""

import json

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolOutcome,
    DeclineRecordingToolInput,
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
