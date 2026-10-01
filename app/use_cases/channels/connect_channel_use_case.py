import re
from typing import NamedTuple

from typed_time_provider import Microseconds, WallClock

from app.contracts.channel_clients import (
    MetaGraphApiClientContract,
    TelegramBotApiClientContract,
)
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories import AuditLogRepoContract, ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels import (
    ChannelView,
    ConnectChannelCommand,
    ConnectChannelRequest,
    MetaPageProfile,
    TelegramBotProfile,
    WhatsAppPhoneNumberProfile,
)
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    MetaObjectId,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    RawChannelSecretInput,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.channels.channel_views import build_channel_view
from app.utilities.channels.channel_endpoints import (
    build_telegram_webhook_path,
    join_public_url,
)
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret

# Token from @BotFather: "<bot id>:<35 characters>".
TELEGRAM_BOT_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"^[0-9]{5,20}:[A-Za-z0-9_\-]{30,100}$"
)
MIN_PAGE_TOKEN_LENGTH: int = 20
MAX_PAGE_TOKEN_LENGTH: int = 1024
CONNECTABLE_CHANNELS: frozenset[ChannelKind] = frozenset(
    {
        ChannelKind.TELEGRAM,
        ChannelKind.WHATSAPP,
        ChannelKind.MESSENGER,
        ChannelKind.INSTAGRAM,
        ChannelKind.WEB_CHAT,
        ChannelKind.PHONE,
    }
)


class _ChannelConnection(NamedTuple):
    """Account and credential a channel was connected with (technical pair)."""

    external_id: ChannelExternalId | None
    secret: ChannelSecret | None


class ConnectChannelUseCase(UseCaseContract[ConnectChannelCommand, ChannelView]):
    """
    Owner connects or reconnects a channel (concept section 6, cabinet
    /channels). One channel per kind per business.

    - Telegram: the @BotFather token is checked with getMe, the webhook is
      set to APP_BASE_URL/v1/channels/telegram/{channel id}/webhook with a
      secret derived from the token; the account is the bot username.
    - WhatsApp: the phone number id from Embedded Signup must be reachable
      with the platform system user token; the app is subscribed to the
      business account's webhooks when its id is given.
    - Messenger / Instagram: the page token must open the page; the app is
      subscribed to the page; Instagram uses the linked professional account.
    - Phone: the assistant line (bought from Zadarma by hand) as E.164.
    - Web chat: switched on, nothing to check.

    Tokens are stored only encrypted. An account already connected to
    another business is refused. Every change is written to the audit log.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        telegram_client: TelegramBotApiClientContract,
        meta_client: MetaGraphApiClientContract,
        phone_number_parser: PhoneNumberParserContract,
        audit_log_repo: AuditLogRepoContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._meta_client: MetaGraphApiClientContract = meta_client
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._storage_scope: StorageScopeContract = storage_scope

    def run(self, input_data: ConnectChannelCommand) -> ChannelView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        if input_data.channel not in CONNECTABLE_CHANNELS:
            raise ValidationFailedError(
                f"The {input_data.channel.value} channel cannot be connected yet."
            )

        now: Microseconds = self._wall_clock.now_unix()
        existing_channel: ChannelDocument | None = find_business_channel(
            self._channel_repo,
            business.id,
            input_data.channel,
        )
        channel: ChannelDocument = existing_channel or ChannelDocument(
            business_id=business.id,
            kind=input_data.channel,
            created_at=now,
            updated_at=now,
        )
        connection: _ChannelConnection = self._connect(
            business,
            channel.id,
            input_data.channel,
            input_data.request,
        )
        channel.external_id = connection.external_id
        channel.encrypted_secret = (
            None
            if connection.secret is None
            else self._secret_cipher.encrypt(connection.secret)
        )
        channel.status = ChannelStatus.CONNECTED
        channel.last_error = None
        channel.last_error_at = None
        channel.updated_at = now
        self._channel_repo.save(channel)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=(
                    AuditAction.CREATE
                    if existing_channel is None
                    else AuditAction.UPDATE
                ),
                entity=AuditEntityName("channel"),
                entity_id=AuditEntityReference(str(channel.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return build_channel_view(channel)

    def _connect(
        self,
        business: BusinessDocument,
        channel_id: ChannelId,
        channel_kind: ChannelKind,
        request: ConnectChannelRequest,
    ) -> _ChannelConnection:
        if channel_kind is ChannelKind.TELEGRAM:
            return self._connect_telegram(business, channel_id, request)

        if channel_kind is ChannelKind.WHATSAPP:
            return self._connect_whatsapp(business, request)

        if channel_kind in (ChannelKind.MESSENGER, ChannelKind.INSTAGRAM):
            return self._connect_page(business, channel_kind, request)

        if channel_kind is ChannelKind.PHONE:
            return self._connect_phone(business, request)

        return _ChannelConnection(external_id=None, secret=None)

    def _connect_telegram(
        self,
        business: BusinessDocument,
        channel_id: ChannelId,
        request: ConnectChannelRequest,
    ) -> _ChannelConnection:
        bot_token: ChannelSecret = read_bot_token(request.bot_token)
        encryption_key: PlatformSecret | None = self._app_settings.encryption_key
        if encryption_key is None:
            raise ExternalServiceError(
                "Telegram cannot be connected: ENCRYPTION_KEY is not configured."
            )

        webhook_url: ChannelWebhookUrl = self._build_webhook_url(
            build_telegram_webhook_path(channel_id)
        )
        profile: TelegramBotProfile = self._telegram_client.get_me(bot_token)
        external_id = ChannelExternalId(str(profile.username))
        self._require_free_account(ChannelKind.TELEGRAM, external_id, business)
        self._telegram_client.set_webhook(
            bot_token,
            webhook_url,
            derive_telegram_webhook_secret(encryption_key, bot_token),
        )
        return _ChannelConnection(external_id=external_id, secret=bot_token)

    def _connect_whatsapp(
        self,
        business: BusinessDocument,
        request: ConnectChannelRequest,
    ) -> _ChannelConnection:
        if request.phone_number_id is None:
            raise ValidationFailedError(
                "phone_number_id from WhatsApp Embedded Signup is required."
            )

        access_token: PlatformSecret | None = (
            self._app_settings.whatsapp_system_user_token
        )
        if access_token is None:
            raise ExternalServiceError(
                "WhatsApp cannot be connected: WHATSAPP_SYSTEM_USER_TOKEN is not "
                "configured."
            )

        profile: WhatsAppPhoneNumberProfile = (
            self._meta_client.get_whatsapp_phone_number(
                access_token,
                request.phone_number_id,
            )
        )
        external_id = ChannelExternalId(str(profile.phone_number_id))
        self._require_free_account(ChannelKind.WHATSAPP, external_id, business)
        if request.whatsapp_business_account_id is not None:
            self._meta_client.subscribe_whatsapp_business_account(
                access_token,
                request.whatsapp_business_account_id,
            )

        return _ChannelConnection(external_id=external_id, secret=None)

    def _connect_page(
        self,
        business: BusinessDocument,
        channel_kind: ChannelKind,
        request: ConnectChannelRequest,
    ) -> _ChannelConnection:
        if request.page_id is None:
            raise ValidationFailedError("page_id of the Facebook page is required.")

        page_token: ChannelSecret = read_page_token(request.page_access_token)
        profile: MetaPageProfile = self._meta_client.get_page(
            page_token, request.page_id
        )
        account_id: MetaObjectId = profile.page_id
        if channel_kind is ChannelKind.INSTAGRAM:
            if profile.instagram_account_id is None:
                raise ValidationFailedError(
                    "No Instagram professional account is linked to this page."
                )

            account_id = profile.instagram_account_id

        external_id = ChannelExternalId(str(account_id))
        self._require_free_account(channel_kind, external_id, business)
        self._meta_client.subscribe_page(page_token, profile.page_id)
        return _ChannelConnection(external_id=external_id, secret=page_token)

    def _connect_phone(
        self,
        business: BusinessDocument,
        request: ConnectChannelRequest,
    ) -> _ChannelConnection:
        if request.phone_number is None:
            raise ValidationFailedError(
                "phone_number of the assistant line is required."
            )

        details: PhoneNumberDetails = self._phone_number_parser.parse(
            request.phone_number,
            request.country_hint or business.country_code,
        )
        external_id = ChannelExternalId(str(details.e164))
        self._require_free_account(ChannelKind.PHONE, external_id, business)
        return _ChannelConnection(external_id=external_id, secret=None)

    def _build_webhook_url(self, path: str) -> ChannelWebhookUrl:
        base_url = self._app_settings.app_base_url
        try:
            return ChannelWebhookUrl(
                join_public_url("" if base_url is None else str(base_url), path)
            )
        except ValueError as error:
            raise ExternalServiceError(
                "Webhooks need a public https APP_BASE_URL; it is missing or not https."
            ) from error

    def _require_free_account(
        self,
        channel_kind: ChannelKind,
        external_id: ChannelExternalId,
        business: BusinessDocument,
    ) -> None:
        # The account may belong to any business: look platform-wide, not
        # only inside the current business's storage scope.
        with self._storage_scope.platform_wide():
            owner_channel: ChannelDocument | None = (
                self._channel_repo.find_by_external_id(channel_kind, external_id)
            )
        if owner_channel is not None and owner_channel.business_id != business.id:
            raise ConflictError(
                f"This {channel_kind.value} account is already connected to "
                "another business."
            )


def read_bot_token(raw_token: RawChannelSecretInput | None) -> ChannelSecret:
    """A @BotFather token, checked for shape (spaces around it are ignored)."""

    token_text: str = "" if raw_token is None else raw_token.strip()
    if TELEGRAM_BOT_TOKEN_PATTERN.fullmatch(token_text) is None:
        raise ValidationFailedError(
            "bot_token must be the token @BotFather gave, like 123456789:AA..."
        )

    return ChannelSecret(token_text)


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
