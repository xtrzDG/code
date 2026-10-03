"""Bearer-token authentication of signed-in users for HTTP routes."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Header

from app.contracts.operator_contract import OperatorContract
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken

type UserAuthenticationOperator = OperatorContract[AccessToken, UserId]
type CurrentUserDependency = Callable[[str | None], UserId]

BEARER_PREFIX: str = "bearer "


def build_current_user_dependency(
    authentication_operator: UserAuthenticationOperator,
) -> CurrentUserDependency:
    """
    Build a FastAPI dependency returning the authenticated UserId.

    Usage in a router builder:
        current_user = build_current_user_dependency(operator)

        @router.get("/v1/businesses")
        def list_businesses(
            user_id: Annotated[UserId, Depends(current_user)],
        ) -> ...
    """

    def resolve_current_user(
        authorization: Annotated[str | None, Header()] = None,
    ) -> UserId:
        access_token: AccessToken = parse_bearer_token(authorization)
        return authentication_operator.operate(access_token)

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
