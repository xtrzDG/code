"""Errors of reading busy times from a calendar outside the platform."""

from app.schemas.constants.calendar_sync import CalendarSyncProblem
from app.schemas.exceptions.application_errors import ExternalServiceError


class BusyTimeSourceError(ExternalServiceError):
    """
    A source of busy times (Google free/busy, an iCal feed, a booking
    system) could not be read. `problem` is the reason the cabinet explains
    to the owner; the message is a short English summary without tokens,
    keys or the secret feed address.
    """

    def __init__(self, message: str, problem: CalendarSyncProblem) -> None:
        super().__init__(message)
        self.problem: CalendarSyncProblem = problem
