"""
Renewing one business's WhatsApp token (Embedded Signup's, 60 days) with
Meta and storing the renewed token in place of the old one, unless the
channel changed meanwhile.
"""

import hmac
import logging

from typed_time_provider import Microseconds

from app.contracts.channel_credentials import MetaTokenRefreshClientContract
from app.contracts.meta_connection import MetaOAuthClientContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.meta_connection import WhatsAppTokenRefreshOutcome
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.channels.meta_provider import MetaAppCredentials, MetaTokenGrants
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
    ProviderRejectedMessageError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.schemas.typings.meta_connection.booleans import (
    IsRefreshedTokenUsable,
    IsSameChannelCredential,
)
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.use_cases.channels.meta_connection.meta_channel_writes import CHANNEL_ENTITY
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.meta_sign_in import (
    WHATSAPP_MANAGEMENT,
    WHATSAPP_MESSAGING,
)
from app.utilities.channels.whatsapp_token_schedule import (
    MINIMUM_EXTENSION_MICROSECONDS,
    describe_end,
)

logger: logging.Logger = logging.getLogger(__name__)
# Meta's answers that say no (to the token, the app or the request): asking
# again soon would get the same answer, so the owners are told.
REFUSALS: tuple[type[ApplicationError], ...] = (
    ValidationFailedError,
    ChannelCredentialRejectedError,
    ProviderRejectedMessageError,
)


class WhatsAppTokenRefresh:
    """
    Meta renews the channel's token (`set_token_expires_in_60_days`) behind
    its circuit breaker; `debug_token` must then say the renewed token
    works, may manage and message the channel's WhatsApp Business Account
    and ends later than the old one. The renewed token is stored with its
    end (encrypted, in one step with the check that the channel still
    holds the old token: the same sealing, or the same token sealed again
    with a newer key) and the audit log notes the change without an actor.
    The old token is never revoked: it keeps working until its own end.

    Outcomes: REFRESHED; REFUSED when Meta says no, the renewed token fails
    its check or the stored one cannot be read; DEFERRED when Meta cannot
    be asked now (a rate limit, an open circuit, an outage); REPLACED when
    the owner reconnected or switched the channel off meanwhile (the
    renewed token is dropped). No token is ever logged.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        refresh_client: MetaTokenRefreshClientContract,
        oauth_client: MetaOAuthClientContract,
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._refresh_client: MetaTokenRefreshClientContract = refresh_client
        self._oauth_client: MetaOAuthClientContract = oauth_client
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def refresh(
        self,
        channel: ChannelDocument,
        app: MetaAppCredentials,
        now: Microseconds,
    ) -> WhatsAppTokenRefreshOutcome:
        if channel.encrypted_secret is None:
            return WhatsAppTokenRefreshOutcome.REPLACED  # No token of its own.

        try:
            current: ChannelSecret = self._secret_cipher.decrypt(
                channel.encrypted_secret
            )
        except ValidationFailedError:
            logger.warning(
                "The WhatsApp token of channel %s cannot be read; not renewed.",
                channel.id,
            )
            return WhatsAppTokenRefreshOutcome.REFUSED

        try:
            renewed: MetaAccessToken = self._refresh_client.refresh_business_token(
                MetaAccessToken(str(current)), app
            )
            grants: MetaTokenGrants = self._oauth_client.read_grants(renewed, app)
        except REFUSALS as error:
            logger.warning(
                "Meta refused to renew the WhatsApp token of channel %s: %s",
                channel.id,
                error,
            )
            return WhatsAppTokenRefreshOutcome.REFUSED
        except ExternalServiceError as error:
            logger.warning(
                "Meta could not renew the WhatsApp token of channel %s now: %s",
                channel.id,
                error,
            )
            return WhatsAppTokenRefreshOutcome.DEFERRED

        if not grants_cover_channel(grants, channel):
            logger.warning(
                "Meta's renewed WhatsApp token of channel %s does not cover its "
                "account or does not end later; the old token stays.",
                channel.id,
            )
            return WhatsAppTokenRefreshOutcome.REFUSED

        return self._store(channel, current, renewed, grants, now)

    def _store(
        self,
        channel: ChannelDocument,
        current: ChannelSecret,
        renewed: MetaAccessToken,
        grants: MetaTokenGrants,
        now: Microseconds,
    ) -> WhatsAppTokenRefreshOutcome:
        sealed: EncryptedChannelSecret = self._secret_cipher.encrypt(
            ChannelSecret(str(renewed))
        )

        def replace(stored: ChannelDocument) -> ChannelDocument | None:
            if (
                not is_channel_active(stored)
                or stored.external_id != channel.external_id
                or not holds_same_credential(
                    stored, channel, current, self._secret_cipher
                )
            ):
                return None  # Reconnected or switched off meanwhile.

            return stored.model_copy(
                update={
                    "encrypted_secret": sealed,
                    "credential_expires_at": grants.expires_at,
                    "credential_checked_at": now,
                    "updated_at": now,
                }
            )

        if self._channel_repo.modify(channel.business_id, channel.id, replace) is None:
            logger.info(
                "WhatsApp channel %s changed while its token was renewed; the "
                "renewed token is dropped.",
                channel.id,
            )
            return WhatsAppTokenRefreshOutcome.REPLACED

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=channel.business_id,
                action=AuditAction.UPDATE,
                entity=CHANNEL_ENTITY,
                entity_id=AuditEntityReference(str(channel.id)),
                created_at=now,
                updated_at=now,
            )
        )
        logger.info(
            "The WhatsApp token of channel %s was renewed; it ends %s.",
            channel.id,
            describe_end(grants.expires_at),
        )
        return WhatsAppTokenRefreshOutcome.REFRESHED


def grants_cover_channel(
    grants: MetaTokenGrants, channel: ChannelDocument
) -> IsRefreshedTokenUsable:
    """
    A renewed token can stand in for the channel's: it may manage and
    message WhatsApp, names the channel's WhatsApp Business Account among
    the accounts it manages, and ends later than the old token (by an hour
    at least; a token without an end is later still).
    """

    account = channel.whatsapp_business_account_id
    if (
        account is None
        or not grants.has(WHATSAPP_MESSAGING)
        or str(account)
        not in {str(target) for target in grants.targets_of(WHATSAPP_MANAGEMENT)}
    ):
        return False

    old_end: Microseconds | None = channel.credential_expires_at
    return (
        grants.expires_at is None
        or old_end is None
        or int(grants.expires_at) >= int(old_end) + MINIMUM_EXTENSION_MICROSECONDS
    )


def holds_same_credential(
    stored: ChannelDocument,
    read: ChannelDocument,
    token: ChannelSecret,
    secret_cipher: SecretCipherAdapterContract,
) -> IsSameChannelCredential:
    """
    The stored channel still holds the token `read` held (`token`): the
    same sealing, or the same token sealed again meanwhile (a key
    rotation), compared in constant time.
    """

    if stored.encrypted_secret is None:
        return False

    if stored.encrypted_secret == read.encrypted_secret:
        return True

    try:
        stored_token: ChannelSecret = secret_cipher.decrypt(stored.encrypted_secret)
    except ValidationFailedError:
        return False

    return hmac.compare_digest(
        str(stored_token).encode("utf-8"), str(token).encode("utf-8")
    )
