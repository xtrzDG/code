"""The platform admin's view of the key ring and its re-encryption runs."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.security import KeyRotationStatus
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.strings import JobErrorText
from app.schemas.typings.security.constrained_integers import (
    EncryptionKeyCount,
    StoredSecretCount,
    WebhookRegistrationCount,
)
from app.schemas.typings.security.prefixed_id import KeyRotationId
from app.schemas.typings.users.prefixed_id import UserId


class KeyRotationView(ImmutableDTO):
    """One re-encryption run and what it found (no secrets, no businesses)."""

    id: KeyRotationId
    status: KeyRotationStatus
    key_count: EncryptionKeyCount
    secrets_total: StoredSecretCount
    secrets_current: StoredSecretCount
    secrets_rotated: StoredSecretCount
    secrets_unreadable: StoredSecretCount
    webhooks_renewed: WebhookRegistrationCount
    webhooks_failed: WebhookRegistrationCount
    requested_at: Microseconds
    started_at: Microseconds | None = None
    finished_at: Microseconds | None = None
    last_error: JobErrorText | None = None


class EncryptionKeysQuery(ImmutableDTO):
    user_id: UserId


class EncryptionKeysView(ImmutableDTO):
    """
    How many keys the ring holds now and the latest re-encryption run
    (None before the first one).
    """

    key_count: EncryptionKeyCount
    latest_rotation: KeyRotationView | None = None


class StartKeyRotationCommand(ImmutableDTO):
    user_id: UserId
    client_ip_address: ClientIpAddress | None = None


class KeyRotationStarted(ImmutableDTO):
    rotation: KeyRotationView
    audit_log_entry_id: AuditLogEntryId


class KeyRotationJobPayload(ImmutableDTO):
    """The queued job's payload: which run it carries out."""

    rotation_id: KeyRotationId
