"""The assistant's offer_choices tool: options to tap under the reply."""

import json

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolOutcome,
    OfferChoicesToolInput,
)
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.use_cases.conversations.tools.tool_outcomes import error_outcome

SHOWN_NOTE: str = (
    "The options will appear under your reply, after prompt_text. Now write "
    "the reply without listing them; the customer's tap comes back as the "
    "option's text, or as its number on a channel without buttons."
)


def run_offer_choices(
    call: LlmToolCall, context: AssistantToolContext
) -> AssistantToolOutcome:
    """
    The options go with this turn's reply (a later call in the turn
    replaces them). Repeated options are refused, so every tap names one
    option; a phone call has nothing to tap. The result does not repeat the
    options, so they never count as evidence for the reply guard, which
    checks them with the reply instead.
    """

    if context.channel is ChannelKind.PHONE:
        return error_outcome(call, "Options cannot be shown on a phone call.")

    tool_input = OfferChoicesToolInput.model_validate_json(call.input_json)
    seen: set[str] = set()
    for option in tool_input.options:
        key: str = str(option).casefold()
        if key in seen:
            return error_outcome(
                call, f"The option '{option}' is given twice; give each once."
            )
        seen.add(key)

    return AssistantToolOutcome(
        tool_name=call.tool_name,
        result=LlmToolResult(
            call_id=call.call_id,
            result_json=LlmToolResultJson(
                json.dumps(
                    {"shown": len(tool_input.options), "note": SHOWN_NOTE},
                    ensure_ascii=False,
                )
            ),
        ),
        choices=ReplyChoices(
            prompt=tool_input.prompt_text, options=list(tool_input.options)
        ),
    )
