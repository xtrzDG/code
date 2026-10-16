from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, ChannelStatus, WidgetPosition
from app.schemas.constants.deliveries import DeliveryFailureReason
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
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    MetaPageUsername,
    WhatsAppNumberDigits,
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
    A Meta-approved message template staff replies travel in once the
    WhatsApp 24-hour window has closed: its name and the language it was
    approved in. Its body has a single parameter, the staff text. A
    channel keeps one per language (`ChannelDocument.whatsapp_staff_templates`).
    """

    name: WhatsAppTemplateName
    language_code: WhatsAppTemplateLanguageCode


class ChannelPublicProfile(PersistentDocument):
    """
    The public address customers open a chat with, learned when the channel
    is connected: the WhatsApp number, the Facebook page's username, the
    Instagram account's username (each None when the platform did not say).
    The Telegram bot's username is the channel's external id.
    """

    whatsapp_number: WhatsAppNumberDigits | None = None
    page_username: MetaPageUsername | None = None
    instagram_username: InstagramUsername | None = None


class ChannelDocument(BaseDocument):
    """
    A connected customer channel (concept table `channels`).

    Credentials are stored only encrypted with the platform key. When the
    platform refuses the credential the status becomes ERROR with a short
    reason and its time; the next successful delivery (or a reconnect)
    clears them. A WhatsApp channel may name the template staff replies
    use outside the 24-hour window.

    Version 2: `public_profile`, the public address for share links and QR
    codes (optional: channels connected earlier have none until they are
    reconnected).

    Version 3: `credential_expires_at` and `credential_checked_at`, when a
    Meta channel's token runs out (None: it never does, or nobody asked
    Meta yet) and when the daily check last asked; both optional.

    Version 4: the channel's health and per-language staff templates, all
    optional. `whatsapp_staff_templates` holds one approved template per
    language (unique `language_code`); staff replies take the one of the
    conversation's language, then the business's default language
    (`app/utilities/channels/staff_templates.py`). The single
    `whatsapp_staff_template` of version 3 is still written (the template
    of the default language, else the first) for the previous release, and
    version 3 rows read it as a one-template list (upcaster).
    `last_inbound_at` and `last_outbound_at` are when the platform last
    brought a customer message and last took one of ours (to the minute:
    `app/utilities/channels/channel_activity.py`); `last_error_reason`
    classifies `last_error` in the cabinet's terms (None for a reason
    written before version 4).
    """

    schema_version: SchemaVersion = SchemaVersion("4")
    id: ChannelId = Field(default_factory=ChannelId)
    business_id: BusinessId
    kind: ChannelKind
    external_id: ChannelExternalId | None = None
    encrypted_secret: EncryptedChannelSecret | None = None
    status: ChannelStatus = ChannelStatus.PENDING
    last_error: ChannelErrorSummary | None = None
    last_error_at: Microseconds | None = None
    last_error_reason: DeliveryFailureReason | None = None
    web_chat_appearance: WebChatAppearance | None = None
    whatsapp_staff_template: WhatsAppStaffTemplate | None = None
    whatsapp_staff_templates: list[WhatsAppStaffTemplate] = Field(
        default_factory=list[WhatsAppStaffTemplate]
    )
    public_profile: ChannelPublicProfile | None = None
    credential_expires_at: Microseconds | None = None
    credential_checked_at: Microseconds | None = None
    last_inbound_at: Microseconds | None = None
    last_outbound_at: Microseconds | None = None
