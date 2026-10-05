"""Bearer-token authentication of signed-in users for HTTP routes."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Header, Request
from starlette.concurrency import run_in_threadpool

from app.contracts.operator_contract import OperatorContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.gateways.http.request_limits import limit_class_of
from app.gateways.http.strict_request_parsing import read_client_ip_address
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import SessionCheck
from app.schemas.dto.spend_guard import ApiRequestAdmission
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.utilities.security.user_agents import read_user_agent

type UserAuthenticationOperator = OperatorContract[SessionCheck, SessionAssurance]
type CurrentUserDependency = Callable[
    [Request, str | None], Coroutine[Any, Any, UserId]
]

BEARER_PREFIX: str = "bearer "
# Methods that only look: platform support with a read-only grant may use
# them. Everything else changes something.
READING_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})


def build_current_user_dependency(
    authentication_operator: UserAuthenticationOperator,
    session_assurance: SessionAssuranceContract,
    admit_request: OperatorContract[ApiRequestAdmission, None] | None = None,
) -> CurrentUserDependency:
    """
    Build a FastAPI dependency returning the authenticated UserId.

    It also binds the request's session (how it was signed in, when its
    person last proved it is them, the caller's address, and whether the
    request reads or changes) for the use cases that check two-factor
    sign-in, step-up and platform support's access. The session's last
    use (address and browser) is recorded on the way. With `admit_request`
    the request then counts against the person's generic limits (429 with
    Retry-After past them; exports stricter, `request_limits`), and a
    request whose token is refused against its client address.

    The dependency is async on purpose: it binds the session in the
    request's own task, whose context the route's worker
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
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> UserId:
        client_ip_address: ClientIpAddress | None = read_client_ip_address(request)
        try:
            check = SessionCheck(
                access_token=parse_bearer_token(authorization),
                client_ip_address=client_ip_address,
                user_agent=read_user_agent(request.headers.get("user-agent")),
                access_mode=access_mode_of(request.method),
            )
            assurance: SessionAssurance = await run_in_threadpool(
                authentication_operator.operate, check
            )
        except AuthenticationRequiredError:
            # A refused token counts against its address, as no token does:
            # a made-up header buys no way around the per-address limit.
            if admit_request is not None and client_ip_address is not None:
                await run_in_threadpool(
                    admit_request.operate,
                    ApiRequestAdmission(client_ip_address=client_ip_address),
                )
            raise

        session_assurance.bind(assurance)
        if admit_request is not None:
            await run_in_threadpool(
                admit_request.operate,
                ApiRequestAdmission(
                    user_id=assurance.user_id,
                    limit_class=limit_class_of(request.url.path),
                ),
            )
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


def access_mode_of(method: str) -> BusinessAccessMode:
    """READ for the methods that only look, WRITE for every other."""

    return (
        BusinessAccessMode.READ
        if method.upper() in READING_METHODS
        else BusinessAccessMode.WRITE
    )
