"""Keep abc order."""

from base_typed_string import BaseTypedString


class DatabaseUrl(BaseTypedString):
    """Postgres connection string (contains credentials; never logged)."""


class PlatformIdentifier(BaseTypedString):
    """Non-secret identifier at a provider (app id, project id, merchant id)."""


class PlatformSecret(BaseTypedString):
    """Platform-level credential (API key, webhook secret). Never logged."""


# Keep abc order for all non example types, if possible.
