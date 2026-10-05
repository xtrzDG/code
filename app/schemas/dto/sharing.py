"""Sharing the assistant: the hosted chat page, channel links and QR codes."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.channels import WidgetPosition
from app.schemas.constants.sharing import ShareLinkGap, ShareLinkKind
from app.schemas.domain.business_privacy_settings import (
    DEFAULT_CONVERSATION_RETENTION_DAYS,
    DEFAULT_LLM_TURN_RETENTION_DAYS,
)
from app.schemas.dto.channels.widget import WidgetLanguageView
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.booleans import IsWebChatEnabled
from app.schemas.typings.channels.constrained_strings import (
    PublicBaseUrl,
    WidgetAccentColor,
    WidgetScriptUrl,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.privacy.constrained_integers import (
    ConversationRetentionDays,
    LlmTurnRetentionDays,
)
from app.schemas.typings.sharing.constrained_strings import (
    BusinessPublicSlug,
    HostedChatUrl,
    ShareLinkUrl,
    ShareSourceTag,
)
from app.schemas.typings.sharing.strings import ShareLinkLabel
from app.schemas.typings.users.prefixed_id import UserId


class ShareLinkView(ImmutableDTO):
    """
    One way customers open a conversation: its link (with the source tag
    where the platform carries one invisibly: `?src=` on the hosted page,
    `?ref=` on m.me and ig.me) and how it names the account. `url` is None
    with a `gap` when a channel that is switched on has no link yet.
    """

    kind: ShareLinkKind
    url: ShareLinkUrl | None = None
    label: ShareLinkLabel | None = None
    gap: ShareLinkGap | None = None


class ShareLinksQuery(ImmutableDTO):
    """Ask for a business's share links, tagged with where they will be put."""

    user_id: UserId
    business_id: BusinessId
    source: ShareSourceTag | None = None


class ShareLinksView(ImmutableDTO):
    """
    Everything the owner shares: the hosted chat page's address (`slug`,
    `hosted_chat_url`: None until CABINET_BASE_URL is set) and a link per
    channel that is switched on, hosted page first. `source` is the tag the
    links carry.
    """

    business_id: BusinessId
    slug: BusinessPublicSlug
    hosted_chat_url: HostedChatUrl | None = None
    source: ShareSourceTag | None = None
    links: list[ShareLinkView]


class PublicSlugRequest(ImmutableDTO):
    """HTTP body of "change the chat address": the new slug."""

    slug: BusinessPublicSlug


class PublicSlugCommand(ImmutableDTO):
    """An owner gives the business's hosted chat page a new address."""

    user_id: UserId
    business_id: BusinessId
    request: PublicSlugRequest


class HostedChatLookup(ImmutableDTO):
    """
    A visitor opens /c/{address}: the address is a slug or, for a business
    that has none yet, its id. The id is not named `business_id`: the
    business is known only once the address is resolved.
    """

    slug: BusinessPublicSlug | None = None
    requested_business_id: BusinessId | None = None


class HostedChatView(ImmutableDTO):
    """
    What the hosted chat page needs before the widget loads: the business,
    its current address (`slug`; a page opened under an older address or
    the id moves there), its name, colour and customer languages, whether
    the chat is on, where the widget script and API live (None while
    APP_BASE_URL is not set), and the privacy notice with how long the
    business keeps conversations and the records of model calls (its
    Settings → Privacy, the defaults until it chose).
    """

    business_id: BusinessId
    slug: BusinessPublicSlug | None = None
    business_name: BusinessName
    is_enabled: IsWebChatEnabled
    default_language: LanguageTag
    languages: list[WidgetLanguageView]
    accent_color: WidgetAccentColor | None = None
    position: WidgetPosition | None = None
    api_base_url: PublicBaseUrl | None = None
    widget_script_url: WidgetScriptUrl | None = None
    privacy_url: WebLink | None = None
    conversation_retention_days: ConversationRetentionDays = (
        DEFAULT_CONVERSATION_RETENTION_DAYS
    )
    llm_turn_retention_days: LlmTurnRetentionDays = DEFAULT_LLM_TURN_RETENTION_DAYS
