from typed_time_provider import Microseconds, WallClock

from app.contracts.operations import (
    CalendarAuthorizationStateRepoContract,
    CalendarConnectionRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
)
from app.schemas.dto.operations import (
    CalendarConnectionView,
    CalendarTokenGrant,
    CompleteCalendarConnectionCommand,
)
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.strings import ExternalCalendarId
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.calendar.calendar_state import hash_authorization_state
from app.utilities.scheduling.zoned_time import MICROSECONDS_PER_SECOND

PRIMARY_CALENDAR_ID: ExternalCalendarId = ExternalCalendarId("primary")


class CompleteGoogleCalendarConnectionUseCase(
    UseCaseContract[CompleteCalendarConnectionCommand, CalendarConnectionView]
):
    """
    OAuth callback: the state must be one we issued, unused and unexpired
    (it is consumed before the code exchange, so a callback cannot be
    replayed). Google's code is exchanged for tokens; the refresh token is
    stored only encrypted, and the business's primary calendar becomes the
    connected calendar (replacing an earlier connection).
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
    ) -> CalendarConnectionView:
        now: Microseconds = self._wall_clock.now_unix()
        state: CalendarAuthorizationStateDocument | None = (
            self._authorization_state_repo.find_by_state_hash(
                hash_authorization_state(input_data.state)
            )
        )
        if state is None or state.is_consumed or int(state.expires_at) <= int(now):
            raise ValidationFailedError(
                "The calendar connection link has expired or was already used. "
                "Start connecting again."
            )

        state.is_consumed = True
        state.updated_at = now
        self._authorization_state_repo.save(state)
        grant: CalendarTokenGrant = self._calendar_client.exchange_code(input_data.code)
        if grant.refresh_token is None:
            raise ExternalServiceError(
                "Google did not grant offline access. Remove the app's access in "
                "the Google account and connect again."
            )

        connection = CalendarConnectionDocument(
            business_id=state.business_id,
            calendar_id=PRIMARY_CALENDAR_ID,
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
        return CalendarConnectionView(
            business_id=connection.business_id,
            calendar_id=connection.calendar_id,
            connected_at=now,
        )
