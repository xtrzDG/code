from typed_time_provider import Microseconds, WallClock

from app.contracts.operations import (
    CalendarAuthorizationStateRepoContract,
    GoogleCalendarClientContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.calendar import CalendarAuthorizationStateDocument
from app.schemas.dto.operations.calendar_connection import (
    CalendarConnectUrlView,
    StartCalendarConnectionCommand,
)
from app.schemas.typings.bookings.constrained_strings import CalendarAuthorizationUrl
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.bookings.strings import (
    CalendarAuthorizationState,
    CalendarCodeVerifier,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.calendar.calendar_state import (
    code_challenge_of,
    generate_authorization_state,
    generate_code_verifier,
    hash_authorization_state,
)
from app.use_cases.shared.business_access import require_business
from app.utilities.scheduling.zoned_time import MICROSECONDS_PER_SECOND

AUTHORIZATION_STATE_LIFETIME_SECONDS: int = 10 * 60


class StartGoogleCalendarConnectionUseCase(
    UseCaseContract[StartCalendarConnectionCommand, CalendarConnectUrlView]
):
    """
    Owner starts connecting Google Calendar: a one-time state bound to the
    business, the owner and the session they ask from is stored (hashed)
    for ten minutes with the flow's PKCE code verifier (sealed), and the
    Google consent link asking for offline access to calendar events, with
    the verifier's S256 challenge, is returned. Needs the request's session
    (the completion must come back on the same one).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        authorization_state_repo: CalendarAuthorizationStateRepoContract,
        calendar_client: GoogleCalendarClientContract,
        wall_clock: WallClock[Microseconds],
        session_assurance: SessionAssuranceContract,
        secret_cipher: SecretCipherAdapterContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._authorization_state_repo: CalendarAuthorizationStateRepoContract = (
            authorization_state_repo
        )
        self._calendar_client: GoogleCalendarClientContract = calendar_client
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def run(self, input_data: StartCalendarConnectionCommand) -> CalendarConnectUrlView:
        require_business(self._business_repo, input_data.business_id)
        session: SessionAssurance | None = self._session_assurance.current()
        if session is None or session.user_id != input_data.user_id:
            raise AuthenticationRequiredError("Sign in to connect Google Calendar.")

        state: CalendarAuthorizationState = generate_authorization_state()
        verifier: CalendarCodeVerifier = generate_code_verifier()
        authorization_url: CalendarAuthorizationUrl = (
            self._calendar_client.build_authorization_url(
                state, code_challenge_of(verifier)
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        expires_at = Microseconds(
            int(now) + AUTHORIZATION_STATE_LIFETIME_SECONDS * MICROSECONDS_PER_SECOND
        )
        self._authorization_state_repo.save(
            CalendarAuthorizationStateDocument(
                business_id=input_data.business_id,
                user_id=input_data.user_id,
                state_hash=hash_authorization_state(state),
                expires_at=expires_at,
                session_id=session.session_id,
                sealed_code_verifier=self._secret_cipher.encrypt(
                    ChannelSecret(str(verifier))
                ),
                created_at=now,
                updated_at=now,
            )
        )
        return CalendarConnectUrlView(
            authorization_url=authorization_url,
            expires_at=expires_at,
        )
