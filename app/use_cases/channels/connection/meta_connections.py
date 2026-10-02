"""Connect WhatsApp, Messenger and Instagram accounts through the Graph API."""

from app.contracts.channel_clients import MetaGraphApiClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.channel_settings import ConnectChannelRequest
from app.schemas.dto.channels.provider_profiles import (
    MetaPageProfile,
    WhatsAppPhoneNumberProfile,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    RawChannelSecretInput,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.channels.connection.channel_connection import (
    AccountCheck,
    ChannelConnection,
)

MIN_PAGE_TOKEN_LENGTH: int = 20
MAX_PAGE_TOKEN_LENGTH: int = 1024


def read_page_token(raw_token: RawChannelSecretInput | None) -> ChannelSecret:
    """A page access token from Facebook Login, checked for shape."""

    token_text: str = "" if raw_token is None else raw_token.strip()
    if (
        not MIN_PAGE_TOKEN_LENGTH <= len(token_text) <= MAX_PAGE_TOKEN_LENGTH
        or not token_text.isascii()
        or any(character.isspace() for character in token_text)
    ):
        raise ValidationFailedError("page_access_token is missing or malformed.")

    return ChannelSecret(token_text)


def connect_whatsapp(
    meta_client: MetaGraphApiClientContract,
    app_settings: AppSettings,
    require_free_account: AccountCheck,
    request: ConnectChannelRequest,
) -> ChannelConnection:
    if request.phone_number_id is None:
        raise ValidationFailedError(
            "phone_number_id from WhatsApp Manager (API setup) is required."
        )

    access_token: PlatformSecret | None = app_settings.whatsapp_system_user_token
    if access_token is None:
        raise ExternalServiceError(
            "WhatsApp cannot be connected: WHATSAPP_SYSTEM_USER_TOKEN is not "
            "configured."
        )

    profile: WhatsAppPhoneNumberProfile = meta_client.get_whatsapp_phone_number(
        access_token,
        request.phone_number_id,
    )
    external_id = ChannelExternalId(str(profile.phone_number_id))
    require_free_account(ChannelKind.WHATSAPP, external_id)
    if request.whatsapp_business_account_id is not None:
        meta_client.subscribe_whatsapp_business_account(
            access_token,
            request.whatsapp_business_account_id,
        )

    return ChannelConnection(external_id=external_id, secret=None)


def connect_page(
    meta_client: MetaGraphApiClientContract,
    require_free_account: AccountCheck,
    channel_kind: ChannelKind,
    request: ConnectChannelRequest,
) -> ChannelConnection:
    if request.page_id is None:
        raise ValidationFailedError("page_id of the Facebook page is required.")

    page_token: ChannelSecret = read_page_token(request.page_access_token)
    profile: MetaPageProfile = meta_client.get_page(page_token, request.page_id)
    account_id: MetaObjectId = profile.page_id
    if channel_kind is ChannelKind.INSTAGRAM:
        if profile.instagram_account_id is None:
            raise ValidationFailedError(
                "No Instagram professional account is linked to this page."
            )

        account_id = profile.instagram_account_id

    external_id = ChannelExternalId(str(account_id))
    require_free_account(channel_kind, external_id)
    meta_client.subscribe_page(page_token, profile.page_id)
    return ChannelConnection(external_id=external_id, secret=page_token)
