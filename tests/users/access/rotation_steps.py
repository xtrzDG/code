"""Steps of the session rotation tests: requests as a session, proofs, rotations."""

from collections.abc import Callable
from contextvars import copy_context

from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import RotateSessionCommand, SessionProof
from app.schemas.dto.users import LoginSessionView
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.users.constrained_strings import SessionRotationTicket
from app.transformers.users.user_view_transformer import UserViewTransformer
from app.use_cases.users.sessions.rotate_session_use_case import RotateSessionUseCase
from app.use_cases.users.sessions.session_proofs import record_proof
from app.utilities.security.access_tokens import hash_access_token
from app.utilities.security.require_recent_authentication import (
    RequireRecentAuthentication,
)
from tests.users.access.session_steps import check
from tests.users.accounts_testbed import AccountsTestbed


def as_request[T](
    testbed: AccountsTestbed, session: LoginSessionView, work: Callable[[], T]
) -> T:
    """Run `work` as a request of this session, at the level it really has."""

    def request() -> T:
        testbed.session_assurance.bind(testbed.authenticate_user.run(check(session)))
        return work()

    return copy_context().run(request)


def stored(testbed: AccountsTestbed, session: LoginSessionView) -> UserSessionDocument:
    found = testbed.user_session_repo.find_by_token_hash(
        hash_access_token(session.access_token)
    )
    assert found is not None
    return found


def prove(
    testbed: AccountsTestbed,
    session: LoginSessionView,
    auth_level: AuthLevel = AuthLevel.TWO_FACTOR,
) -> SessionProof:
    """The person of `session` proves it is them now (a step-up)."""

    return as_request(
        testbed,
        session,
        lambda: record_proof(
            testbed.session_assurance,
            testbed.user_session_repo,
            session.user.id,
            auth_level,
            testbed.clock.build_wall_clock().now_unix(),
        ),
    )


def raise_level(
    testbed: AccountsTestbed, session: LoginSessionView
) -> SessionRotationTicket:
    """A proof that raises the one-factor `session`: its rotation ticket."""

    ticket = prove(testbed, session).rotation_ticket
    assert ticket is not None
    return ticket


def rotation(testbed: AccountsTestbed) -> RotateSessionUseCase:
    return RotateSessionUseCase(
        user_repo=testbed.user_repo,
        user_session_repo=testbed.user_session_repo,
        session_assurance=testbed.session_assurance,
        user_view_transformer=UserViewTransformer(),
        app_settings=testbed.settings,
        wall_clock=testbed.clock.build_wall_clock(),
    )


def rotate(
    testbed: AccountsTestbed, session: LoginSessionView, ticket: SessionRotationTicket
) -> LoginSessionView:
    return as_request(
        testbed,
        session,
        lambda: rotation(testbed).run(
            RotateSessionCommand(user_id=session.user.id, rotation_ticket=ticket)
        ),
    )


def may_confirm_sensitive_actions(
    testbed: AccountsTestbed, session: LoginSessionView
) -> bool:
    """Whether a step-up-guarded action would pass for this token now."""

    guard = RequireRecentAuthentication(
        testbed.session_assurance,
        testbed.clock.build_wall_clock(),
        testbed.settings.step_up_max_age_seconds,
    )

    def attempt() -> bool:
        try:
            guard.require_recent_authentication()
        except StepUpRequiredError:
            return False
        return True

    return as_request(testbed, session, attempt)
