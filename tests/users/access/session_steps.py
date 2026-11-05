"""Browsers, addresses and steps shared by the device session tests."""

from collections.abc import Callable
from contextvars import copy_context

from app.schemas.constants.mfa import AuthLevel
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import SessionCheck
from app.schemas.dto.users import LoginSessionView
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.utilities.security.user_agents import read_user_agent
from tests.users.accounts_testbed import AccountsTestbed

MAC_CHROME: str = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
IPHONE_SAFARI: str = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
)
ANDROID_CHROME: str = (
    "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
)
HOME_IP: str = "203.0.113.7"
CAFE_IP: str = "198.51.100.23"
MINUTE: int = 60
HOUR: int = 60 * MINUTE
DAY: int = 24 * HOUR


def check(
    session: LoginSessionView,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> SessionCheck:
    """One signed-in request of this session."""

    return SessionCheck(
        access_token=session.access_token,
        client_ip_address=None if client_ip is None else ClientIpAddress(client_ip),
        user_agent=read_user_agent(user_agent),
    )


def in_session[T](
    testbed: AccountsTestbed,
    session: LoginSessionView,
    work: Callable[[], T],
) -> T:
    """Run `work` as a request of this session (the gateway binds it)."""

    def request() -> T:
        assurance: SessionAssurance = testbed.authenticate_user.run(check(session))
        testbed.session_assurance.bind(
            assurance.model_copy(update={"auth_level": AuthLevel.TWO_FACTOR})
        )
        return work()

    return copy_context().run(request)
