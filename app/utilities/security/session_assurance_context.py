from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token

from app.contracts.session_assurance import SessionAssuranceContract
from app.schemas.dto.mfa import SessionAssurance


class SessionAssuranceContext(SessionAssuranceContract):
    """
    The signed-in session of the request being served, in a context
    variable.

    The HTTP gateway binds it in the request's own task once the bearer
    token is checked (an async dependency), so the route's worker thread,
    which starts with a copy of the task's context, sees it; another
    request, a job or a new thread never does. Code that runs with none is
    background work.
    """

    def __init__(self) -> None:
        self._current: ContextVar[SessionAssurance | None] = ContextVar(
            "session_assurance", default=None
        )

    def current(self) -> SessionAssurance | None:
        return self._current.get()

    def bind(self, assurance: SessionAssurance) -> None:
        # The request's task ends with the request: nothing to reset.
        self._current.set(assurance)

    @contextmanager
    def assured(self, assurance: SessionAssurance) -> Generator[SessionAssurance]:
        token: Token[SessionAssurance | None] = self._current.set(assurance)
        try:
            yield assurance
        finally:
            self._current.reset(token)
