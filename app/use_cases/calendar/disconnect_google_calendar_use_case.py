import logging

from app.contracts.operations import (
    CalendarConnectionRepoContract,
    CalendarEventLinkRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.calendar import CalendarConnectionDocument
from app.schemas.dto.operations.calendar_connection import (
    CalendarDisconnectResult,
    DisconnectCalendarCommand,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.strings import CalendarRefreshToken

LOGGER: logging.Logger = logging.getLogger(__name__)


class DisconnectGoogleCalendarUseCase(
    UseCaseContract[DisconnectCalendarCommand, CalendarDisconnectResult]
):
    """
    Owner disconnects Google Calendar: the refresh token is revoked at Google
    (best effort; a failed revocation is logged), the stored tokens and the
    booking-to-event links are deleted. Existing events stay in the calendar.
    Disconnecting a business without a connection is harmless.
    """

    def __init__(
        self,
        connection_repo: CalendarConnectionRepoContract,
        event_link_repo: CalendarEventLinkRepoContract,
        calendar_client: GoogleCalendarClientContract,
        secret_cipher: SecretCipherAdapterContract,
    ) -> None:
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._event_link_repo: CalendarEventLinkRepoContract = event_link_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def run(self, input_data: DisconnectCalendarCommand) -> CalendarDisconnectResult:
        connection: CalendarConnectionDocument | None = (
            self._connection_repo.get_by_business(input_data.business_id)
        )
        if connection is None:
            return CalendarDisconnectResult(
                business_id=input_data.business_id, was_connected=False
            )

        try:
            self._calendar_client.revoke_token(
                CalendarRefreshToken(
                    str(self._secret_cipher.decrypt(connection.encrypted_refresh_token))
                )
            )
        except ApplicationError as error:
            LOGGER.warning("Google token revocation failed: %s", error)

        for link in self._event_link_repo.list_by_business(input_data.business_id):
            self._event_link_repo.delete_by_booking(link.business_id, link.booking_id)

        self._connection_repo.delete_by_business(input_data.business_id)
        return CalendarDisconnectResult(
            business_id=input_data.business_id, was_connected=True
        )
