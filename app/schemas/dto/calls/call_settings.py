"""Settings → Calls: what happens after the calls, and the latest text-backs."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    MissedCallSource,
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.booleans import (
    IsCallSummaryEnabled,
    IsSmsFallbackEnabled,
    IsTextBackEnabled,
)
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.channels.booleans import IsChannelConnected
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.notifications.booleans import IsProviderReady
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class CallSettingsRequest(ImmutableDTO):
    """
    The owner's choices: summaries to staff after every call, a message
    to a caller who did not get through (on WhatsApp, in the approved
    template `text_back_template_name`, else by SMS when allowed).
    """

    is_summary_enabled: IsCallSummaryEnabled = True
    is_text_back_enabled: IsTextBackEnabled = False
    text_back_template_name: WhatsAppTemplateName | None = None
    is_sms_fallback_enabled: IsSmsFallbackEnabled = True


class CallSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class UpdateCallSettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: CallSettingsRequest


class TextBackTemplatePreview(ImmutableDTO):
    """
    The text-back in one language: the body to register as the WhatsApp
    template (its one parameter {{1}} is the business name) and how a
    caller reads it.
    """

    language: LanguageTag
    template_body: MessageText
    example: MessageText


class CallSettingsView(ImmutableDTO):
    """
    The settings with what they rely on: whether the business's WhatsApp
    number is connected, whether the platform can send SMS, and the
    text-back in each language of the business.
    """

    is_summary_enabled: IsCallSummaryEnabled
    is_text_back_enabled: IsTextBackEnabled
    text_back_template_name: WhatsAppTemplateName | None = None
    is_sms_fallback_enabled: IsSmsFallbackEnabled
    is_whatsapp_connected: IsChannelConnected
    is_sms_available: IsProviderReady
    template_previews: list[TextBackTemplatePreview] = Field(
        default_factory=list[TextBackTemplatePreview]
    )


class TextBackPageQuery(ImmutableDTO):
    """The business's missed calls, newest first (owners, audited as a view)."""

    user_id: UserId
    business_id: BusinessId
    page: PageRequest = PageRequest()
    client_ip_address: ClientIpAddress | None = None


class TextBackView(ImmutableDTO):
    """One caller who did not get through, and what became of their message."""

    id: MissedCallId
    reason: MissedCallReason
    source: MissedCallSource
    caller_phone_number: E164PhoneNumber | None = None
    called_at: Microseconds
    language: LanguageTag
    status: TextBackStatus
    skip_reason: TextBackSkipReason | None = None
    channel: TextBackChannel | None = None
    conversation_id: ConversationId | None = None
    sent_at: Microseconds | None = None
    last_error: DeliveryErrorText | None = None


class TextBackPage(ImmutableDTO):
    items: list[TextBackView]
    next_cursor: PageCursor | None = None
