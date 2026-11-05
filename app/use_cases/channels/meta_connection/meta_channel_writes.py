"""
Storing a channel a Facebook sign-in connected: the account, its encrypted
credential and public address, an audit entry and the product event, as
the manual connection does (`connection/connect_channel_use_case.py`).
"""

from collections.abc import Callable
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.channels.connection.channel_connection import ChannelConnection
from app.utilities.analytics.product_event_drafts import channel_connected_events
from app.utilities.channels.delivery_targets import find_business_channel

CHANNEL_ENTITY: AuditEntityName = AuditEntityName("channel")


@dataclass(frozen=True)
class MetaChannelStores:
    """Where a connected channel is written, audited and counted."""

    channel_repo: ChannelRepoContract
    secret_cipher: SecretCipherAdapterContract
    audit_log_repo: AuditLogRepoContract
    product_events: RecordProductEventFacilitatorContract
    storage_scope: StorageScopeContract


def require_free_account(
    stores: MetaChannelStores,
    business_id: BusinessId,
    kind: ChannelKind,
    external_id: ChannelExternalId,
) -> None:
    """
    An account already connected to another business is refused (looked up
    platform-wide: it may belong to any business).
    """

    with stores.storage_scope.platform_wide():
        owner_channel: ChannelDocument | None = stores.channel_repo.find_by_external_id(
            kind, external_id
        )
    if owner_channel is not None and owner_channel.business_id != business_id:
        raise ConflictError(
            f"This {kind.value} account is already connected to another business."
        )


def save_connected_channel(
    stores: MetaChannelStores,
    business_id: BusinessId,
    user_id: UserId,
    kind: ChannelKind,
    connection: ChannelConnection,
    now: Microseconds,
    client_ip_address: ClientIpAddress | None,
    complete: Callable[[ChannelDocument], None] = lambda channel: None,
) -> ChannelDocument:
    """
    Connect (or reconnect) the business's channel of a kind with the
    account, credential and public address of `connection`; `complete`
    sets what the kind keeps besides (WhatsApp's business account and
    registration PIN). Errors of an earlier delivery are cleared.
    """

    existing: ChannelDocument | None = find_business_channel(
        stores.channel_repo, business_id, kind
    )
    channel: ChannelDocument = existing or ChannelDocument(
        business_id=business_id, kind=kind, created_at=now, updated_at=now
    )
    channel.external_id = connection.external_id
    channel.encrypted_secret = (
        None
        if connection.secret is None
        else stores.secret_cipher.encrypt(connection.secret)
    )
    channel.public_profile = connection.public_profile
    channel.status = ChannelStatus.CONNECTED
    channel.last_error = None
    channel.last_error_at = None
    channel.last_error_reason = None
    complete(channel)
    channel.updated_at = now
    stores.channel_repo.save(channel)
    stores.audit_log_repo.append(
        AuditLogEntryDocument(
            business_id=business_id,
            actor_id=user_id,
            action=AuditAction.CREATE if existing is None else AuditAction.UPDATE,
            entity=CHANNEL_ENTITY,
            entity_id=AuditEntityReference(str(channel.id)),
            ip_address=client_ip_address,
            created_at=now,
            updated_at=now,
        )
    )
    stores.product_events.record(*channel_connected_events(user_id, business_id, kind))
    return channel
