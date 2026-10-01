"""Bearer-token authentication of business owners for HTTP routes."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Header

from app.contracts.operator_contract import OperatorContract
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.accounts.prefixed_id import OwnerId
from app.schemas.typings.accounts.strings import AccessToken

type OwnerAuthenticationOperator = OperatorContract[AccessToken, OwnerId]
type CurrentOwnerDependency = Callable[[str | None], OwnerId]

BEARER_PREFIX: str = "bearer "


def build_current_owner_dependency(
    authentication_operator: OwnerAuthenticationOperator,
) -> CurrentOwnerDependency:
    """
    Build a FastAPI dependency returning the authenticated OwnerId.

    Usage in a router builder:
        current_owner = build_current_owner_dependency(operator)

        @router.get("/v1/businesses")
        def list_businesses(
            owner_id: Annotated[OwnerId, Depends(current_owner)],
        ) -> ...
    """

    def resolve_current_owner(
        authorization: Annotated[str | None, Header()] = None,
    ) -> OwnerId:
        access_token: AccessToken = parse_bearer_token(authorization)
        return authentication_operator.operate(access_token)

    return resolve_current_owner


def parse_bearer_token(authorization: str | None) -> AccessToken:
    if authorization is None:
        raise AuthenticationRequiredError("Authorization header is missing.")

    if not authorization.lower().startswith(BEARER_PREFIX):
        raise AuthenticationRequiredError("Authorization must use the Bearer scheme.")

    raw_token: str = authorization[len(BEARER_PREFIX) :].strip()
    if raw_token == "":
        raise AuthenticationRequiredError("Bearer token is empty.")

    return AccessToken(raw_token)
