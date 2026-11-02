"""Errors that say a provider itself is in trouble, not the request."""

from app.schemas.exceptions.application_errors import ExternalServiceError


class ProviderOutageError(ExternalServiceError):
    """
    A provider did not answer (a timeout, a connection or read error) or
    answered with a server error (HTTP 5xx): the provider is in trouble,
    not the request or the business's setting. It counts against the
    provider's circuit breaker (REL-04); trying again later can succeed.
    """
