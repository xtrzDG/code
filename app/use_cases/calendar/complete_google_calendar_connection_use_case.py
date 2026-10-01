import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.operations import (
    CalendarAuthorizationStateRepoContract,
    CalendarConnectionRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calendar import CalendarConnectionFailure
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
)
from app.schemas.dto.calendar import CalendarConnectionOutcome
from app.schemas.dto.operations import (
    CalendarConnectionView,
    CalendarTokenGrant,
    CompleteCalendarConnectionCommand,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationCode,
    CalendarDisplayName,
    ExternalCalendarId,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.calendar.calendar_state import hash_authorization_state
from app.utilities.scheduling.zoned_time import MICROSECONDS_PER_SECOND

LOGGER: logging.Logger = logging.getLogger(__name__)
PRIMARY_CALENDAR_ID: ExternalCalendarId = ExternalCalendarId("primary")
# Google's error when the owner declines on the consent page.
ACCESS_DENIED_ERROR: str = "access_denied"


class CompleteGoogleCalendarConnectionUseCase(
    UseCaseContract[CompleteCalendarConnectionCommand, CalendarConnectionOutcome]
):
    """
    OAuth callback: the state must be one we issued, unused and unexpired
    (it is consumed before the code exchange, so a callback cannot be
    replayed), and it must be brought back by the user who started the flow:
    a consent link forwarded to someone else cannot attach their Google
    account to the business that issued it (login CSRF). Another user's
    state is reported as an expired link, without its business and without
    consuming it. Google's code is exchanged for tokens; the refresh token is
    stored only encrypted, and the business's primary calendar becomes the
    connected calendar (replacing an earlier connection), with its title
    when Google tells it.

    Nothing is raised for the expected failures (the owner declined, an old
    or used link, no offline access, Google unavailable): the outcome names
    the reason and, whenever the state is one we issued, the business, so
    the owner is sent back to that business's Channels page.
    """

    def __init__(
        self,
        authorization_state_repo: CalendarAuthorizationStateRepoContract,
        connection_repo: CalendarConnectionRepoContract,
        calendar_client: GoogleCalendarClientContract,
        secret_cipher: SecretCipherAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorization_state_repo: CalendarAuthorizationStateRepoContract = (
            authorization_state_repo
        )
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(
        self,
        input_data: CompleteCalendarConnectionCommand,
    ) -> CalendarConnectionOutcome:
        now: Microseconds = self._wall_clock.now_unix()
        state: CalendarAuthorizationStateDocument | None = (
            None
            if input_data.state is None
            else self._authorization_state_repo.find_by_state_hash(
                hash_authorization_state(input_data.state)
            )
        )
        if state is None or state.user_id != input_data.user_id:
            return CalendarConnectionOutcome(
                failure=CalendarConnectionFailure.LINK_EXPIRED
            )

        if state.is_consumed or int(state.expires_at) <= int(now):
            return CalendarConnectionOutcome(
                business_id=state.business_id,
                failure=CalendarConnectionFailure.LINK_EXPIRED,
            )

        state.is_consumed = True
        state.updated_at = now
        self._authorization_state_repo.save(state)
        if input_data.provider_error is not None or input_data.code is None:
            return CalendarConnectionOutcome(
                business_id=state.business_id,
                failure=(
                    CalendarConnectionFailure.ACCESS_DENIED
                    if input_data.provider_error is None
                    or str(input_data.provider_error) == ACCESS_DENIED_ERROR
                    else CalendarConnectionFailure.PROVIDER_ERROR
                ),
            )

        return self._connect(state, input_data.code, now)

    def _connect(
        self,
        state: CalendarAuthorizationStateDocument,
        code: CalendarAuthorizationCode,
        now: Microseconds,
    ) -> CalendarConnectionOutcome:
        try:
            grant: CalendarTokenGrant = self._calendar_client.exchange_code(code)
        except ExternalServiceError as error:
            LOGGER.warning("Google Calendar code exchange failed: %s", error)
            return CalendarConnectionOutcome(
                business_id=state.business_id,
                failure=CalendarConnectionFailure.PROVIDER_ERROR,
            )

        if grant.refresh_token is None:
            return CalendarConnectionOutcome(
                business_id=state.business_id,
                failure=CalendarConnectionFailure.NO_OFFLINE_ACCESS,
            )

        connection = CalendarConnectionDocument(
            business_id=state.business_id,
            calendar_id=PRIMARY_CALENDAR_ID,
            calendar_name=self._find_calendar_name(grant),
            encrypted_refresh_token=self._secret_cipher.encrypt(
                ChannelSecret(str(grant.refresh_token))
            ),
            encrypted_access_token=self._secret_cipher.encrypt(
                ChannelSecret(str(grant.access_token))
            ),
            access_token_expires_at=Microseconds(
                int(now) + int(grant.expires_in) * MICROSECONDS_PER_SECOND
            ),
            connected_by=state.user_id,
            created_at=now,
            updated_at=now,
        )
        self._connection_repo.save(connection)
        return CalendarConnectionOutcome(
            business_id=connection.business_id,
            connection=CalendarConnectionView(
                business_id=connection.business_id,
                calendar_id=connection.calendar_id,
                connected_at=now,
            ),
        )

    def _find_calendar_name(
        self,
        grant: CalendarTokenGrant,
    ) -> CalendarDisplayName | None:
        """The calendar's title; a failed lookup never stops the connection."""

        try:
            return self._calendar_client.get_calendar_name(
                grant.access_token, PRIMARY_CALENDAR_ID
            )
        except ExternalServiceError as error:
            LOGGER.info("Google Calendar title lookup failed: %s", error)
            return None
