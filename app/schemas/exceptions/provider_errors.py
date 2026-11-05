"""Errors that say a provider itself is in trouble, not the request."""

from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.calendar_sync_errors import BusyTimeSourceError


class ProviderOutageError(ExternalServiceError):
    """
    A provider did not answer (a timeout, a connection or read error) or
    answered with a server error (HTTP 5xx): the provider is in trouble,
    not the request or the business's setting. It counts against the
    provider's circuit breaker (REL-04); trying again later can succeed.
    """


class BusyTimeSourceOutageError(BusyTimeSourceError):
    """
    A busy-time source at a provider (Google Calendar, Cal.com) answered
    with a server error (HTTP 5xx). The cabinet explains it as any answer
    it could not use (PROVIDER_ERROR); it counts against the provider's
    circuit breaker (REL-04), as a read it did not answer does.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, CalendarSyncProblem.PROVIDER_ERROR)
