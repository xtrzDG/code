"""Connect or reconnect a channel of a business."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.channel_clients import (
    MetaGraphApiClientContract,
    TelegramBotApiClientContract,
)
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.session_assurance import StepUpGuardContract
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
from app.schemas.dto.channels.channel_settings import (
    ChannelView,
    ConnectChannelCommand,
    ConnectChannelRequest,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.channels.channel_views import build_channel_view
from app.use_cases.channels.connection.channel_connection import ChannelConnection
from app.use_cases.channels.connection.meta_connections import (
    connect_page,
    connect_whatsapp,
)
from app.use_cases.channels.connection.phone_connection import connect_phone
from app.use_cases.channels.connection.telegram_connection import connect_telegram
from app.use_cases.channels.connection.web_chat_appearance import (
    merge_web_chat_appearance,
)
from app.utilities.analytics.product_event_drafts import (
    channel_connected_events,
)
from app.utilities.channels.delivery_targets import find_business_channel

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


class ConnectChannelUseCase(UseCaseContract[ConnectChannelCommand, ChannelView]):
    """
    Owner connects or reconnects a channel (concept section 6, cabinet
    /channels). One channel per kind per business.

    - Telegram: the @BotFather token is checked with getMe, the webhook is
      set to APP_BASE_URL/v1/channels/telegram/{channel id}/webhook with a
      secret derived from the token; the account is the bot username.
    - WhatsApp: the phone number id from WhatsApp Manager (API setup) must
      be reachable with the platform system user token (the business shares
      its WhatsApp Business account with the platform's portfolio, see
      docs/LAUNCH.md); the app is subscribed to the business account's
      webhooks when its id is given.
    - Messenger / Instagram: the page token must open the page; the app is
      subscribed to the page; Instagram uses the linked professional account.
    - Phone: the assistant line (bought from Zadarma by hand) as E.164.
    - Web chat: switched on, nothing to check; the widget's colour and
      launcher corner are saved (fields left out keep their values).

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
        product_events: RecordProductEventFacilitatorContract,
        step_up: StepUpGuardContract,
    ) -> None:
        self._step_up: StepUpGuardContract = step_up
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
        self._product_events: RecordProductEventFacilitatorContract = product_events

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

        if input_data.channel is not ChannelKind.WEB_CHAT:
            # Credentials of an outside account: only a recently proved person.
            self._step_up.require_recent_authentication()

        if input_data.channel is not ChannelKind.WEB_CHAT and (
            input_data.request.widget_color is not None
            or input_data.request.widget_position is not None
        ):
            raise ValidationFailedError(
                "widget_color and widget_position are settings of the website chat."
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
        connection: ChannelConnection = self._connect(
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
        channel.public_profile = connection.public_profile
        channel.status = ChannelStatus.CONNECTED
        channel.last_error = None
        channel.last_error_at = None
        channel.last_error_reason = None
        if input_data.channel is ChannelKind.WEB_CHAT:
            channel.web_chat_appearance = merge_web_chat_appearance(
                channel.web_chat_appearance, input_data.request
            )

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
        self._product_events.record(
            *channel_connected_events(
                input_data.user_id, business.id, input_data.channel
            )
        )
        return build_channel_view(channel)

    def _connect(
        self,
        business: BusinessDocument,
        channel_id: ChannelId,
        channel_kind: ChannelKind,
        request: ConnectChannelRequest,
    ) -> ChannelConnection:
        def require_free_account(
            kind: ChannelKind,
            external_id: ChannelExternalId,
        ) -> None:
            self._require_free_account(kind, external_id, business)

        if channel_kind is ChannelKind.TELEGRAM:
            return connect_telegram(
                self._telegram_client,
                self._app_settings,
                require_free_account,
                channel_id,
                request,
            )

        if channel_kind is ChannelKind.WHATSAPP:
            return connect_whatsapp(
                self._meta_client, self._app_settings, require_free_account, request
            )

        if channel_kind in (ChannelKind.MESSENGER, ChannelKind.INSTAGRAM):
            return connect_page(
                self._meta_client, require_free_account, channel_kind, request
            )

        if channel_kind is ChannelKind.PHONE:
            return connect_phone(
                self._phone_number_parser, require_free_account, business, request
            )

        return ChannelConnection(external_id=None, secret=None)

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
