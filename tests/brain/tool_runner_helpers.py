"""
Running one assistant tool on a brain world, with a turn context and booking input.
"""

import json
from typing import Any

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
)
from app.schemas.dto.conversations import LlmToolCall
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import LlmToolCallId, LlmToolInputJson
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.brain.brain_world import BrainWorld


def build_context(world: BrainWorld, **changes: Any) -> AssistantToolContext:
    context = AssistantToolContext(
        business_id=world.business.id,
        business_country_code=world.business.country_code,
        contact_id=ContactId(),
        contact_phone_number=E164PhoneNumber("+995577000111"),
        conversation_id=ConversationId(),
        channel=ChannelKind.TELEGRAM,
        language=LanguageTag("ka"),
        available_tools=list(AssistantToolName),
    )
    return context.model_copy(update=changes)


def run_tool(
    world: BrainWorld,
    tool_name: AssistantToolName,
    arguments: dict[str, Any] | str,
    context: AssistantToolContext | None = None,
) -> tuple[dict[str, Any], bool]:
    outcome = world.run_tool.run(
        AssistantToolInvocation(
            context=context if context is not None else build_context(world),
            call=LlmToolCall(
                call_id=LlmToolCallId("call_1"),
                tool_name=tool_name,
                input_json=LlmToolInputJson(
                    arguments
                    if isinstance(arguments, str)
                    else json.dumps(arguments, ensure_ascii=False)
                ),
            ),
        )
    )
    assert outcome.result.call_id == "call_1"
    return json.loads(outcome.result.result_json), outcome.result.is_error


BOOKING_ARGUMENTS: dict[str, Any] = {
    "name": "Nino",
    "phone": None,
    "resource_type": "table",
    "date": "2026-10-02",
    "time": "19:30",
    "party_size": 4,
    "duration_minutes": None,
    "nights": None,
    "notes": "window seat",
}
