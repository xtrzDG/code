"""
The widget testbed with the rating route mounted, and helpers for the
visitor's chat: a turn the worker answers, a rating, the stored review.
"""

from typing import Any

from app.gateways.http.widget_rating_routes import build_widget_rating_router
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import (
    ConversationDocument,
    MessageDocument,
    ToolCallRecord,
)
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmToolInputJson,
    LlmToolResultJson,
    MessageText,
)
from app.use_cases.channels.ratings.rate_widget_conversation_use_case import (
    RateWidgetConversationUseCase,
)
from tests.channels.channels_http import wrap_use_case
from tests.channels.test_widget import SESSION_KEY
from tests.channels.widget_upload_bed import WidgetUploadBed


class WidgetRatingBed(WidgetUploadBed):
    """A widget whose visitors can rate the chat, over the channels testbed."""

    def __init__(self) -> None:
        super().__init__()
        testbed = self.testbed
        self.client.app.include_router(  # type: ignore[attr-defined]
            build_widget_rating_router(
                wrap_use_case(
                    RateWidgetConversationUseCase(
                        testbed.business_repo,
                        testbed.channel_repo,
                        testbed.conversation_repo,
                        testbed.conversation_repo,
                        testbed.message_repo,
                        testbed.widget_rate_limits,
                        testbed.wall_clock,
                    )
                )
            )
        )

    def chat(self, text: str, session_key: str = SESSION_KEY) -> None:
        """The visitor writes and the worker answers ("Reply: <text>")."""

        assert self.send([], text, session_key=session_key).status_code == 202
        self.testbed.run_worker()

    def rate(
        self,
        rating: str,
        reason: str | None = None,
        message_id: object | None = None,
        session_key: str = SESSION_KEY,
        business_id: object | None = None,
    ) -> Any:
        body: dict[str, Any] = {"session_key": session_key, "rating": rating}
        if reason is not None:
            body["reason"] = reason
        if message_id is not None:
            body["message_id"] = str(message_id)
        return self.client.post(
            f"/v1/widget/{business_id or self.business.id}/rating", json=body
        )

    def conversation(self, session_key: str = SESSION_KEY) -> ConversationDocument:
        [conversation] = self.testbed.conversation_repo.list_by_channel_user(
            self.business.id, ChannelKind.WEB_CHAT, ChannelUserId(session_key)
        )
        return conversation

    def messages(self, session_key: str = SESSION_KEY) -> list[MessageDocument]:
        return self.testbed.message_repo.list_by_conversation(
            self.business.id, self.conversation(session_key).id
        )

    def answers(self, session_key: str = SESSION_KEY) -> list[MessageDocument]:
        return [
            message
            for message in self.messages(session_key)
            if message.author is MessageAuthor.ASSISTANT
        ]

    def store_booking_answer(self, tool: AssistantToolName) -> MessageDocument:
        """An answer of a turn that called `tool` (booked, or took a lead)."""

        conversation = self.conversation()
        now = self.testbed.wall_clock.now_unix()
        answer = MessageDocument(
            conversation_id=conversation.id,
            business_id=conversation.business_id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.ASSISTANT,
            text=MessageText("Booked: Friday at 19:00, a table for two."),
            tool_calls=[
                ToolCallRecord(
                    tool_name=tool,
                    input_json=LlmToolInputJson("{}"),
                    result_json=LlmToolResultJson('{"ok": true}'),
                )
            ],
            created_at=now,
            updated_at=now,
        )
        self.testbed.message_repo.save(answer)
        return answer
