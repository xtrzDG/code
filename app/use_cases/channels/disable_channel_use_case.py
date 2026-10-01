import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.repositories import AuditLogRepoContract, ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.channels import ChannelView, DisableChannelCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.channels.channel_views import build_channel_view
from app.utilities.channels.delivery_targets import (
    decrypt_channel_secret,
    find_business_channel,
)

logger: logging.Logger = logging.getLogger(__name__)


class DisableChannelUseCase(UseCaseContract[DisableChannelCommand, ChannelView]):
    """
    Owner switches a channel off.

    The credential is erased and the account released (another business may
    connect it later); messages that still arrive for it are dropped. A
    Telegram bot's webhook is removed when Telegram can be reached.
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
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: DisableChannelCommand) -> ChannelView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        channel: ChannelDocument | None = find_business_channel(
            self._channel_repo,
            business.id,
            input_data.channel,
        )
        if channel is None:
            raise NotFoundError(
                f"The {input_data.channel.value} channel is not connected."
            )

        if channel.kind is ChannelKind.TELEGRAM:
            self._remove_telegram_webhook(channel)

        now: Microseconds = self._wall_clock.now_unix()
        channel.status = ChannelStatus.DISABLED
        channel.encrypted_secret = None
        channel.external_id = None
        channel.updated_at = now
        self._channel_repo.save(channel)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.DELETE,
                entity=AuditEntityName("channel"),
                entity_id=AuditEntityReference(str(channel.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return build_channel_view(channel)

    def _remove_telegram_webhook(self, channel: ChannelDocument) -> None:
        try:
            bot_token: ChannelSecret | None = decrypt_channel_secret(
                channel,
                self._secret_cipher,
            )
            if bot_token is not None:
                self._telegram_client.delete_webhook(bot_token)
        except ApplicationError as error:
            logger.warning(
                "The webhook of Telegram channel %s was not removed: %s",
                channel.id,
                error,
            )
