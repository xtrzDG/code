"""Bearer-token authentication of signed-in users for HTTP routes."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Header
from starlette.concurrency import run_in_threadpool

from app.contracts.operator_contract import OperatorContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken

type UserAuthenticationOperator = OperatorContract[AccessToken, SessionAssurance]
type CurrentUserDependency = Callable[[str | None], Coroutine[Any, Any, UserId]]

BEARER_PREFIX: str = "bearer "


def build_current_user_dependency(
    authentication_operator: UserAuthenticationOperator,
    session_assurance: SessionAssuranceContract,
) -> CurrentUserDependency:
    """
    Build a FastAPI dependency returning the authenticated UserId.

    It also binds the request's session (how it was signed in, when its
    person last proved it is them) for the use cases that check two-factor
    sign-in and step-up. The dependency is async on purpose: it binds the
    session in the request's own task, whose context the route's worker
    thread copies; a sync dependency would bind it in a thread of its own,
    and the route would never see it. The token check itself runs in the
    thread pool, like any blocking work.

    Usage in a router builder:
        current_user = build_current_user_dependency(operator, assurance)

        @router.get("/v1/businesses")
        def list_businesses(
            user_id: Annotated[UserId, Depends(current_user)],
        ) -> ...
    """

    async def resolve_current_user(
        authorization: Annotated[str | None, Header()] = None,
    ) -> UserId:
        access_token: AccessToken = parse_bearer_token(authorization)
        assurance: SessionAssurance = await run_in_threadpool(
            authentication_operator.operate, access_token
        )
        session_assurance.bind(assurance)
        return assurance.user_id

    return resolve_current_user


def parse_bearer_token(authorization: str | None) -> AccessToken:
    if authorization is None:
        raise AuthenticationRequiredError("Authorization header is missing.")

    if not authorization.lower().startswith(BEARER_PREFIX):
        raise AuthenticationRequiredError("Authorization must use the Bearer scheme.")

    raw_token: str = authorization[len(BEARER_PREFIX) :].strip()
    if raw_token == "":
        raise AuthenticationRequiredError("Bearer token is empty.")

    return AccessToken(raw_token)
