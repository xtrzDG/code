"""The website chat's colour and launcher corner, as saved and as changed."""

from app.schemas.domain.channels import WebChatAppearance
from app.schemas.dto.channels.channel_settings import ConnectChannelRequest


def merge_web_chat_appearance(
    saved: WebChatAppearance | None,
    request: ConnectChannelRequest,
) -> WebChatAppearance:
    """The saved widget look with the request's new colour or corner."""

    return WebChatAppearance(
        accent_color=(
            request.widget_color
            if request.widget_color is not None
            else None
            if saved is None
            else saved.accent_color
        ),
        position=(
            request.widget_position
            if request.widget_position is not None
            else None
            if saved is None
            else saved.position
        ),
    )
