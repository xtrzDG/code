from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.security import KeyRotationStatus
from app.schemas.typings.platform.strings import JobErrorText
from app.schemas.typings.security.constrained_integers import (
    EncryptionKeyCount,
    StoredSecretCount,
    WebhookRegistrationCount,
)
from app.schemas.typings.security.prefixed_id import KeyRotationId
from app.schemas.typings.users.prefixed_id import UserId


class KeyRotationDocument(BaseDocument):
    """
    The latest re-encryption of the stored secrets with the current key of
    the ring (platform-wide; one document, replaced by each new run).

    The counts say whether a previous key may be dropped: every secret is
    `current` (it was already) or `rotated` (moved now), none `unreadable`
    (no key of the ring opens it: such a channel must be reconnected), and
    every Telegram webhook was registered again with the current key's
    secret (`webhooks_failed` is zero). Runs are audited (entity
    `encryption_keys`).
    """

    id: KeyRotationId = Field(default_factory=KeyRotationId)
    status: KeyRotationStatus = KeyRotationStatus.QUEUED
    requested_by: UserId
    key_count: EncryptionKeyCount
    secrets_total: StoredSecretCount = StoredSecretCount(0)
    secrets_current: StoredSecretCount = StoredSecretCount(0)
    secrets_rotated: StoredSecretCount = StoredSecretCount(0)
    secrets_unreadable: StoredSecretCount = StoredSecretCount(0)
    webhooks_renewed: WebhookRegistrationCount = WebhookRegistrationCount(0)
    webhooks_failed: WebhookRegistrationCount = WebhookRegistrationCount(0)
    started_at: Microseconds | None = None
    finished_at: Microseconds | None = None
    last_error: JobErrorText | None = None
