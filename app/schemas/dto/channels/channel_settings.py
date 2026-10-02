"""The cabinet's connected channels: connecting, disabling and listing them."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, ChannelStatus, WidgetPosition
from app.schemas.dto.staff_reply_templates import WhatsAppStaffTemplateView
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.booleans import HasChannelCredential
from app.schemas.typings.channels.constrained_strings import (
    ChannelErrorSummary,
    MetaObjectId,
    WidgetAccentColor,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    RawChannelSecretInput,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId


class ConnectChannelRequest(ImmutableDTO):
    """
    HTTP body that connects a channel; the fields needed depend on the kind.

    - telegram: `bot_token` from @BotFather.
    - whatsapp: `phone_number_id` from WhatsApp Manager (API setup) and, to
      subscribe the app to its webhooks, `whatsapp_business_account_id`.
    - messenger, instagram: `page_id` and `page_access_token` (Facebook
      Login); Instagram uses the professional account linked to the page.
    - phone: `phone_number` of the assistant line (any country; national
      formats are read in `country_hint` or the business country).
    - web_chat: nothing to switch it on; optionally `widget_color` (hex brand
      colour) and `widget_position` (left or right) for the widget. Fields
      left out keep their saved values.
    """

    bot_token: RawChannelSecretInput | None = Field(default=None, repr=False)
    phone_number_id: MetaObjectId | None = None
    whatsapp_business_account_id: MetaObjectId | None = None
    page_id: MetaObjectId | None = None
    page_access_token: RawChannelSecretInput | None = Field(default=None, repr=False)
    phone_number: RawPhoneNumberInput | None = None
    country_hint: CountryCode | None = None
    widget_color: WidgetAccentColor | None = None
    widget_position: WidgetPosition | None = None


class ConnectChannelCommand(ImmutableDTO):
    """Owner connects (or reconnects) one channel of a business."""

    user_id: UserId
    business_id: BusinessId
    channel: ChannelKind
    request: ConnectChannelRequest
    client_ip_address: ClientIpAddress | None = None


class DisableChannelCommand(ImmutableDTO):
    """Owner switches a channel off; its credential is erased."""

    user_id: UserId
    business_id: BusinessId
    channel: ChannelKind
    client_ip_address: ClientIpAddress | None = None


class ChannelListQuery(ImmutableDTO):
    """List the channels of a business for a signed-in member."""

    user_id: UserId
    business_id: BusinessId


class ChannelView(ImmutableDTO):
    """
    A channel as the cabinet shows it; credentials are never returned.

    `account_id` is the public account inside the channel: bot username,
    WhatsApp phone number id, page id, Instagram account id, or the E.164
    number of the assistant line. With status ERROR, `last_error` is the
    platform's short reason (no secrets) and `last_error_at` its time. The
    website chat also reports its saved colour and launcher corner (None:
    the widget's defaults). WhatsApp reports the template staff replies use
    once the 24-hour window has closed (None: no template, such replies are
    refused).
    """

    id: ChannelId
    business_id: BusinessId
    channel: ChannelKind
    status: ChannelStatus
    account_id: ChannelExternalId | None = None
    has_credential: HasChannelCredential
    updated_at: Microseconds
    last_error: ChannelErrorSummary | None = None
    last_error_at: Microseconds | None = None
    widget_color: WidgetAccentColor | None = None
    widget_position: WidgetPosition | None = None
    staff_reply_template: WhatsAppStaffTemplateView | None = None
