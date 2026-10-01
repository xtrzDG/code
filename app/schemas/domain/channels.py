from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, ChannelStatus, WidgetPosition
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    ChannelErrorSummary,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
    WidgetAccentColor,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    EncryptedChannelSecret,
)


class WebChatAppearance(PersistentDocument):
    """
    How the website chat looks on the business's site: its brand colour and
    the launcher's corner (None: the widget's defaults). Attributes on the
    embed tag (data-color, data-position) still override them.
    """

    accent_color: WidgetAccentColor | None = None
    position: WidgetPosition | None = None


class WhatsAppStaffTemplate(PersistentDocument):
    """
    The Meta-approved message template staff replies travel in once the
    WhatsApp 24-hour window has closed: its name and the language it was
    approved in. Its body has a single parameter, the staff text.
    """

    name: WhatsAppTemplateName
    language_code: WhatsAppTemplateLanguageCode


class ChannelDocument(BaseDocument):
    """
    A connected customer channel (concept table `channels`).

    Credentials are stored only encrypted with the platform key. When the
    platform refuses the credential the status becomes ERROR with a short
    reason and its time; the next successful delivery (or a reconnect)
    clears them. A WhatsApp channel may name the template staff replies
    use outside the 24-hour window.
    """

    id: ChannelId = Field(default_factory=ChannelId)
    business_id: BusinessId
    kind: ChannelKind
    external_id: ChannelExternalId | None = None
    encrypted_secret: EncryptedChannelSecret | None = None
    status: ChannelStatus = ChannelStatus.PENDING
    last_error: ChannelErrorSummary | None = None
    last_error_at: Microseconds | None = None
    web_chat_appearance: WebChatAppearance | None = None
    whatsapp_staff_template: WhatsAppStaffTemplate | None = None
