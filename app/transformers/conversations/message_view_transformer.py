from app.contracts.transformer_contract import TransformerContract
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.conversation_feed.conversation_views import (
    MessageView,
    ToolCallView,
)


class MessageViewTransformer(TransformerContract[MessageDocument, MessageView]):
    """A stored message with its tool calls, model, tokens and cost."""

    def transform(self, input_data: MessageDocument) -> MessageView:
        return MessageView(
            id=input_data.id,
            direction=input_data.direction,
            author=input_data.author,
            text=input_data.text,
            language=input_data.language,
            sent_by=input_data.sent_by,
            tool_calls=[
                ToolCallView(
                    tool_name=record.tool_name,
                    input_json=record.input_json,
                    result_json=record.result_json,
                    is_error=record.is_error,
                )
                for record in input_data.tool_calls
            ],
            model_id=input_data.model_id,
            input_tokens=input_data.input_tokens,
            output_tokens=input_data.output_tokens,
            cost_micro_usd=input_data.cost_micro_usd,
            created_at=input_data.created_at,
        )
