from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import SessionsQuery, UserSessionList, UserSessionView
from app.schemas.typings.users.prefixed_id import UserSessionId
from app.use_cases.users.sessions.session_views import session_view
from app.utilities.security.session_expiry import is_session_over


class ListMySessionsUseCase(UseCaseContract[SessionsQuery, UserSessionList]):
    """
    The person's signed-in devices (Account → Security): every live
    session with its browser, system, addresses and times, the request's
    own first, then the most recently used. Ended sessions are left out
    (the daily purge deletes them).
    """

    def __init__(
        self,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SessionsQuery) -> UserSessionList:
        now: Microseconds = self._wall_clock.now_unix()
        assurance: SessionAssurance | None = self._session_assurance.current()
        current: UserSessionId | None = (
            assurance.session_id
            if assurance is not None and assurance.user_id == input_data.user_id
            else None
        )
        live: list[UserSessionDocument] = [
            session
            for session in self._user_session_repo.list_by_user(input_data.user_id)
            if not is_session_over(session, now)
        ]
        views: list[UserSessionView] = [
            session_view(session, is_current=session.id == current) for session in live
        ]
        views.sort(key=lambda view: (not view.is_current, -int(view.last_seen_at)))
        return UserSessionList(items=views)
