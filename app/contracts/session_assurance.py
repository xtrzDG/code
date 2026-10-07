"""
How the session of the request being served is signed in, and the step-up
check of sensitive actions.
"""

from typing import Protocol

from app.contracts.utility_contract import UtilityContract
from app.schemas.dto.mfa import SessionAssurance


class SessionAssuranceContract(UtilityContract, Protocol):
    """
    The signed-in session of the request being served. The HTTP gateway
    binds it once the bearer token is checked; background work runs with
    none. Each request (asyncio task) sees its own: the request's worker
    threads inherit it.
    """

    def current(self) -> SessionAssurance | None:
        raise NotImplementedError

    def bind(self, assurance: SessionAssurance) -> None:
        """Hold `assurance` for the rest of the current request."""
        raise NotImplementedError


class StepUpGuardContract(UtilityContract, Protocol):
    """The one-line check of every sensitive action."""

    def require_recent_authentication(self) -> None:
        """
        Pass when the session of this request proved its person within
        STEP_UP_MAX_AGE_SECONDS (sign-in or a passed step-up). Raises
        StepUpRequiredError otherwise, also when no session is bound.
        """
        raise NotImplementedError
