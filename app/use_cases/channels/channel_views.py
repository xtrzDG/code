"""Cabinet view of a channel; credentials never leave the server."""

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.deliveries import DeliveryFailureReason
from app.schemas.domain.channels import (
    ChannelDocument,
    WebChatAppearance,
    WhatsAppStaffTemplate,
)
from app.schemas.dto.channels.channel_settings import ChannelView
from app.schemas.dto.staff_reply_templates import WhatsAppStaffTemplateView
from app.utilities.channels.staff_templates import channel_staff_templates
from app.utilities.sharing.share_links import find_link_state

# Order of channels in the cabinet: free messengers first (concept: cheap
# channels are shown to customers first), then WhatsApp, web and phone.
CHANNEL_DISPLAY_ORDER: tuple[ChannelKind, ...] = (
    ChannelKind.TELEGRAM,
    ChannelKind.INSTAGRAM,
    ChannelKind.MESSENGER,
    ChannelKind.WHATSAPP,
    ChannelKind.WEB_CHAT,
    ChannelKind.PHONE,
    ChannelKind.VIBER,
    ChannelKind.OWNER_TEST,
)


def build_channel_view(channel: ChannelDocument) -> ChannelView:
    appearance: WebChatAppearance | None = channel.web_chat_appearance
    staff_template: WhatsAppStaffTemplate | None = channel.whatsapp_staff_template
    return ChannelView(
        id=channel.id,
        business_id=channel.business_id,
        channel=channel.kind,
        status=channel.status,
        account_id=channel.external_id,
        has_credential=channel.encrypted_secret is not None,
        updated_at=channel.updated_at,
        last_error=channel.last_error,
        last_error_at=channel.last_error_at,
        last_error_reason=explain_channel_error(channel),
        last_inbound_at=channel.last_inbound_at,
        last_outbound_at=channel.last_outbound_at,
        widget_color=None if appearance is None else appearance.accent_color,
        widget_position=None if appearance is None else appearance.position,
        staff_reply_template=(
            None
            if staff_template is None
            else WhatsAppStaffTemplateView(
                name=staff_template.name,
                language_code=staff_template.language_code,
            )
        ),
        staff_reply_templates=[
            WhatsAppStaffTemplateView(
                name=template.name, language_code=template.language_code
            )
            for template in channel_staff_templates(channel)
        ],
        link_state=find_link_state(channel),
    )


def explain_channel_error(channel: ChannelDocument) -> DeliveryFailureReason | None:
    """
    What the channel's last error means; an ERROR written before reasons
    were kept was a refused credential (nothing else puts a channel in
    ERROR).
    """

    if channel.last_error_reason is not None or channel.last_error is None:
        return channel.last_error_reason

    if channel.status is ChannelStatus.ERROR:
        return DeliveryFailureReason.CREDENTIAL_REJECTED

    return None


def sort_channel_views(views: list[ChannelView]) -> list[ChannelView]:
    return sorted(views, key=lambda view: CHANNEL_DISPLAY_ORDER.index(view.channel))
