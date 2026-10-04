from app.contracts.transformer_contract import TransformerContract
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.dto.conversation_feed.conversation_views import (
    MessageView,
    ToolCallView,
)
from app.schemas.dto.media import MessageAttachmentView
from app.utilities.media.attachment_texts import map_link


class MessageViewTransformer(TransformerContract[MessageDocument, MessageView]):
    """
    A stored message with its tool calls, model, tokens and cost, and the
    voice notes, photos and places of a customer message (the storage path
    stays inside: the cabinet asks for a file by its id).
    """

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
            attachments=[
                build_attachment_view(attachment)
                for attachment in input_data.attachments
            ],
        )


def build_attachment_view(attachment: MessageAttachment) -> MessageAttachmentView:
    is_deleted: bool = attachment.media_deleted_at is not None
    return MessageAttachmentView(
        kind=attachment.kind,
        media_id=None if is_deleted else attachment.media_id,
        media_type=attachment.media_type,
        byte_count=attachment.byte_count,
        duration_seconds=attachment.duration_seconds,
        transcript=attachment.transcript,
        location=attachment.location,
        map_url=None if attachment.location is None else map_link(attachment.location),
        problem=attachment.problem,
        is_media_deleted=is_deleted,
    )
