import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.operations import (
    CalendarAuthorizationStateRepoContract,
    CalendarConnectionRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.calendar import CalendarConnectionFailure
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.calendar import CalendarConnectionOutcome
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.operations.calendar_connection import (
    CalendarConnectionView,
    CalendarTokenGrant,
    CompleteCalendarConnectionCommand,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationCode,
    CalendarCodeVerifier,
    CalendarDisplayName,
    ExternalCalendarId,
)
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    EncryptedChannelSecret,
)
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
    replayed), and it must be brought back by the user who started the flow,
    on the session they started it from: a consent link forwarded to
    someone else, or finished from another device, cannot attach a Google
    account to the business that issued it (login CSRF). Another user's or
    another session's state is reported as an expired link, without its
    business and without consuming it. The person must still be an owner of
    the business when they come back (a removed owner gets an expired link,
    without the business). Google's code is exchanged for tokens with the
    flow's PKCE verifier (a code intercepted on its way back is useless
    without it); the refresh token is stored only encrypted, and the
    business's primary calendar becomes the connected calendar (replacing
    an earlier connection), with its title when Google tells it.

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
        session_assurance: SessionAssuranceContract,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
    ) -> None:
        self._authorization_state_repo: CalendarAuthorizationStateRepoContract = (
            authorization_state_repo
        )
        self._connection_repo: CalendarConnectionRepoContract = connection_repo
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access

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
        # Without its PKCE verifier (a state of version 1) a flow never ends.
        sealed_verifier: EncryptedChannelSecret | None = (
            None if state is None else state.sealed_code_verifier
        )
        if (
            state is None
            or sealed_verifier is None
            or not self._is_own_session(state, input_data)
        ):
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

        if not self._is_still_owner(state):
            return CalendarConnectionOutcome(
                failure=CalendarConnectionFailure.LINK_EXPIRED
            )

        return self._connect(state, input_data.code, sealed_verifier, now)

    def _is_own_session(
        self,
        state: CalendarAuthorizationStateDocument,
        input_data: CompleteCalendarConnectionCommand,
    ) -> bool:
        """The person and the session that started the flow."""

        session: SessionAssurance | None = self._session_assurance.current()
        return (
            state.user_id == input_data.user_id
            and state.session_id is not None
            and session is not None
            and session.user_id == input_data.user_id
            and session.session_id == state.session_id
        )

    def _is_still_owner(self, state: CalendarAuthorizationStateDocument) -> bool:
        try:
            self._authorize_business_access.run(
                BusinessAccessRequest(
                    user_id=state.user_id,
                    business_id=state.business_id,
                    required_role=BusinessMemberRole.OWNER,
                )
            )
        except AccessDeniedError, NotFoundError:
            return False
        return True

    def _connect(
        self,
        state: CalendarAuthorizationStateDocument,
        code: CalendarAuthorizationCode,
        sealed_verifier: EncryptedChannelSecret,
        now: Microseconds,
    ) -> CalendarConnectionOutcome:
        verifier = CalendarCodeVerifier(
            str(self._secret_cipher.decrypt(sealed_verifier))
        )
        try:
            grant: CalendarTokenGrant = self._calendar_client.exchange_code(
                code, verifier
            )
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
