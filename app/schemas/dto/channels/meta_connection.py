"""
The cabinet's self-serve Meta connection: WhatsApp Embedded Signup and the
page picker of Messenger and Instagram (Facebook Login).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.meta_connection import MetaConnectionPurpose
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import MetaPageName
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.meta_connection.booleans import (
    HasLinkedInstagramAccount,
    IsMetaSignInAvailable,
)
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConfigurationId,
    MetaConnectionState,
    MetaEmbeddedSignupCode,
    MetaGraphApiVersion,
    MetaLoginCode,
    MetaPermissionName,
    WhatsAppBusinessAccountId,
)
from app.schemas.typings.platform.strings import PlatformIdentifier
from app.schemas.typings.sharing.constrained_strings import (
    InstagramUsername,
    MetaPageUsername,
)
from app.schemas.typings.users.prefixed_id import UserId


class MetaSignInOptionsQuery(ImmutableDTO):
    """Which Facebook sign-ins the Channels page may offer this member."""

    user_id: UserId
    business_id: BusinessId


class MetaSignInOptionsView(ImmutableDTO):
    """
    Whether the cabinet offers "Continue with Facebook": WhatsApp Embedded
    Signup needs the platform's Meta app and its signup configuration
    (META_APP_ID, META_APP_SECRET, META_EMBEDDED_SIGNUP_CONFIG_ID), the page
    picker the app alone. `app_id` and `graph_api_version` are what the
    Facebook SDK starts with (None when nothing is offered).
    """

    whatsapp: IsMetaSignInAvailable
    pages: IsMetaSignInAvailable
    app_id: PlatformIdentifier | None = None
    graph_api_version: MetaGraphApiVersion | None = None


class StartMetaConnectionRequest(ImmutableDTO):
    """HTTP body that starts a Facebook sign-in for one purpose."""

    purpose: MetaConnectionPurpose


class StartMetaConnectionCommand(ImmutableDTO):
    """The owner starts a Facebook sign-in from the Channels page."""

    user_id: UserId
    business_id: BusinessId
    request: StartMetaConnectionRequest


class MetaConnectionStartView(ImmutableDTO):
    """
    What the cabinet's Facebook SDK needs to open Meta's window: the
    one-time `state` to bring back (the cabinet keeps it in memory only),
    the app and Graph API version, and either the Embedded Signup
    `configuration_id` (WhatsApp) or the `permissions` to ask for (pages).
    The sign-in must be finished before `expires_at`.
    """

    purpose: MetaConnectionPurpose
    state: MetaConnectionState
    app_id: PlatformIdentifier
    graph_api_version: MetaGraphApiVersion
    configuration_id: MetaConfigurationId | None = None
    permissions: list[MetaPermissionName] = Field(
        default_factory=list[MetaPermissionName]
    )
    expires_at: Microseconds


class CompleteWhatsAppSignupRequest(ImmutableDTO):
    """
    HTTP body that finishes WhatsApp Embedded Signup: the sign-in's `state`,
    Meta's `code` (valid for seconds), and the business account and number
    Meta's window named when it finished (optional: without them they are
    read from the token's permissions and the account's numbers).
    """

    state: MetaConnectionState
    code: MetaEmbeddedSignupCode = Field(repr=False)
    whatsapp_business_account_id: WhatsAppBusinessAccountId | None = None
    phone_number_id: MetaObjectId | None = None


class CompleteWhatsAppSignupCommand(ImmutableDTO):
    """The owner finished WhatsApp Embedded Signup in Meta's window."""

    user_id: UserId
    business_id: BusinessId
    request: CompleteWhatsAppSignupRequest
    client_ip_address: ClientIpAddress | None = None


class ListMetaPagesRequest(ImmutableDTO):
    """HTTP body with the page picker's sign-in: its `state` and Meta's `code`."""

    state: MetaConnectionState
    code: MetaLoginCode = Field(repr=False)


class ListMetaPagesCommand(ImmutableDTO):
    """The owner signed in with Facebook to pick a page."""

    user_id: UserId
    business_id: BusinessId
    request: ListMetaPagesRequest


class MetaPageView(ImmutableDTO):
    """
    One page of the picker: its name and username, and the Instagram
    professional account linked to it (`has_instagram`; only such pages
    can connect Instagram).
    """

    page_id: MetaObjectId
    name: MetaPageName | None = None
    username: MetaPageUsername | None = None
    has_instagram: HasLinkedInstagramAccount
    instagram_account_id: MetaObjectId | None = None
    instagram_username: InstagramUsername | None = None


class MetaPageList(ImmutableDTO):
    """
    The pages the owner manages (pages linked to an Instagram professional
    account first), to pick one before `expires_at` with the same `state`.
    """

    pages: list[MetaPageView] = Field(default_factory=list[MetaPageView])
    expires_at: Microseconds


class ConnectMetaPageRequest(ImmutableDTO):
    """HTTP body that connects the page the owner picked."""

    state: MetaConnectionState
    page_id: MetaObjectId


class ConnectMetaPageCommand(ImmutableDTO):
    """The owner connects Messenger or Instagram with a picked page."""

    user_id: UserId
    business_id: BusinessId
    channel: ChannelKind
    request: ConnectMetaPageRequest
    client_ip_address: ClientIpAddress | None = None
