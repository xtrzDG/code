"""
What only platform admins see of a conversation (OWASP API3, ASVS
V15.3.1): the inputs and results of the assistant's tool calls, the model
that answered, its tokens and its cost. Owners and staff keep everything
else, the tool calls' names and failures included (the card shows them as
the assistant's actions), so the API answers them without these fields
instead of hiding them in the interface.
"""

from app.schemas.dto.conversation_feed.conversation_actions import StaffMessageResult
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationDetailView,
    MessagePage,
    MessageView,
    ToolCallView,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.typings.users.booleans import IsPlatformAdmin


def team_tool_call(call: ToolCallView) -> ToolCallView:
    """The tool and whether it failed, without what went in and came out."""

    return call.model_copy(update={"input_json": None, "result_json": None})


def team_message(message: MessageView) -> MessageView:
    return message.model_copy(
        update={
            "tool_calls": [team_tool_call(call) for call in message.tool_calls],
            "model_id": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_micro_usd": None,
        }
    )


def conversation_for(
    view: ConversationDetailView, sees_platform_details: IsPlatformAdmin
) -> ConversationDetailView:
    if sees_platform_details:
        return view

    return view.model_copy(
        update={
            "messages": [team_message(message) for message in view.messages],
            "usage": None,
        }
    )


def message_page_for(
    page: MessagePage, sees_platform_details: IsPlatformAdmin
) -> MessagePage:
    if sees_platform_details:
        return page

    return page.model_copy(
        update={"items": [team_message(message) for message in page.items]}
    )


def staff_message_result(result: StaffMessageResult) -> StaffMessageResult:
    """A staff member's message has no model behind it: nothing to hide."""

    return result.model_copy(update={"message": team_message(result.message)})


def reply_for(
    reply: AssistantReply, sees_platform_details: IsPlatformAdmin
) -> AssistantReply:
    if sees_platform_details:
        return reply

    return reply.model_copy(
        update={"tool_calls": [team_tool_call(call) for call in reply.tool_calls]}
    )
