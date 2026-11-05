"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class EncryptionKeyCount(BaseConstrainedTypedInt):
    """How many keys the platform's key ring holds (ENCRYPTION_KEYS)."""

    ge = 1
    le = 32


class StoredSecretCount(BaseConstrainedTypedInt):
    """How many stored encrypted secrets (channel and calendar tokens)."""

    ge = 0


class WebhookRegistrationCount(BaseConstrainedTypedInt):
    """How many channel webhooks were registered again (or failed to be)."""

    ge = 0


# Keep abc order for all non example types, if possible.
