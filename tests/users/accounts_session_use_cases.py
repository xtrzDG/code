"""The accounts testbed's use cases of a person's own sessions, wired."""

from collections.abc import Mapping

from typed_time_provider import Microseconds, WallClock

from app.use_cases.users.logout_use_case import LogoutUseCase
from app.use_cases.users.sessions.list_my_sessions_use_case import (
    ListMySessionsUseCase,
)
from app.use_cases.users.sessions.revoke_other_sessions_use_case import (
    RevokeOtherSessionsUseCase,
)
from app.use_cases.users.sessions.revoke_session_use_case import RevokeSessionUseCase
from tests.users.accounts_repositories import AccountsRepositories
from tests.users.fake_ip_countries import TEST_IP_COUNTRIES, FixedIpCountries


class AccountsSessionUseCases(AccountsRepositories):
    """Signing out, listing one's sessions and ending one or all the others."""

    def __init__(self, environment_variables: Mapping[str, str]) -> None:
        super().__init__(environment_variables)
        wall_clock: WallClock[Microseconds] = self.clock.build_wall_clock()
        self.logout = LogoutUseCase(
            user_session_repo=self.user_session_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.list_my_sessions = ListMySessionsUseCase(
            user_session_repo=self.user_session_repo,
            session_assurance=self.session_assurance,
            wall_clock=wall_clock,
            ip_countries=FixedIpCountries(TEST_IP_COUNTRIES),
        )
        self.revoke_session = RevokeSessionUseCase(
            user_session_repo=self.user_session_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.revoke_other_sessions = RevokeOtherSessionsUseCase(
            user_session_repo=self.user_session_repo,
            session_assurance=self.session_assurance,
            audit_log_repo=self.audit_log_repo,
            wall_clock=wall_clock,
        )
