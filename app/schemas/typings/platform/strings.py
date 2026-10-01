"""Keep abc order."""

from base_typed_string import BaseTypedString


class CorrelationId(BaseTypedString):
    """Identifier that ties logs, traces and errors of one request together."""


class DatabaseUrl(BaseTypedString):
    """Postgres connection string (contains credentials; never logged)."""


class PlatformIdentifier(BaseTypedString):
    """Non-secret identifier at a provider (app id, project id, merchant id)."""


class JobErrorText(BaseTypedString):
    """Last error message of a failed background job (no secrets, no PII)."""


class JobPayloadJson(BaseTypedString):
    """JSON object with the arguments of one queued background job."""


class LocalDirectoryPath(BaseTypedString):
    """Directory on the server's file system (absolute or relative to the cwd)."""


class PlatformSecret(BaseTypedString):
    """Platform-level credential (API key, webhook secret). Never logged."""


# Keep abc order for all non example types, if possible.
