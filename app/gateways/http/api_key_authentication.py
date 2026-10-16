"""
The public API's bearer key: `Authorization: Bearer awk_<prefix>_<secret>`.

A FastAPI dependency checks the key once per request (the answer is kept
on the request, so the Idempotency-Key dependency, which needs the key's
owner, does not check it twice). A refused key counts against its client
address like a refused cabinet token does.
"""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from base_typed_string import BaseTypedStringConstraintViolationError
from fastapi import Header, Request
from starlette.concurrency import run_in_threadpool

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import read_client_ip_address
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.public_api.access import ApiKeyCredentials, ApiKeyPrincipal
from app.schemas.dto.spend_guard import ApiRequestAdmission
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.integrations.constrained_strings import ApiKeyToken
from app.schemas.typings.integrations.prefixed_id import ApiKeyId
from app.schemas.typings.users.prefixed_id import UserId

type ApiKeyAuthentication = Callable[
    [Request, str | None], Coroutine[Any, Any, ApiKeyPrincipal]
]

BEARER_PREFIX: str = "bearer "
PRINCIPAL_STATE: str = "api_key_principal"
KEY_DESCRIPTION: str = (
    "`Bearer awk_…`: an API key from Settings → Integrations → API keys."
)
MISSING_KEY_MESSAGE: str = "Send the API key as `Authorization: Bearer awk_…`."
INVALID_KEY_MESSAGE: str = "The API key is not valid (any more)."


def build_api_key_authentication(
    authenticate: OperatorContract[ApiKeyCredentials, ApiKeyPrincipal],
    admit_request: OperatorContract[ApiRequestAdmission, None] | None = None,
) -> tuple[ApiKeyAuthentication, CurrentUserDependency]:
    """
    The dependency that answers the request's key, and one that answers
    the key's owner (the user Idempotency-Keys belong to).
    """

    async def resolve_api_key(
        request: Request,
        authorization: Annotated[
            str | None, Header(description=KEY_DESCRIPTION)
        ] = None,
    ) -> ApiKeyPrincipal:
        known: object = getattr(request.state, PRINCIPAL_STATE, None)
        if isinstance(known, ApiKeyPrincipal):
            return known

        client_ip_address = read_client_ip_address(request)
        try:
            principal: ApiKeyPrincipal = await run_in_threadpool(
                authenticate.operate,
                ApiKeyCredentials(
                    token=parse_api_key(authorization),
                    client_ip_address=client_ip_address,
                ),
            )
        except AuthenticationRequiredError:
            if admit_request is not None and client_ip_address is not None:
                await run_in_threadpool(
                    admit_request.operate,
                    ApiRequestAdmission(client_ip_address=client_ip_address),
                )
            raise

        setattr(request.state, PRINCIPAL_STATE, principal)
        return principal

    async def resolve_key_owner(
        request: Request,
        authorization: Annotated[
            str | None, Header(description=KEY_DESCRIPTION)
        ] = None,
    ) -> UserId:
        return (await resolve_api_key(request, authorization)).created_by

    return resolve_api_key, resolve_key_owner


def request_api_key_id(request: Request) -> ApiKeyId | None:
    """
    The key a request was authenticated with: its Idempotency-Keys and
    their stored answers are its own, not shared with the owner's other
    keys (the public API's paths name no business).
    """

    known: object = getattr(request.state, PRINCIPAL_STATE, None)
    return known.api_key_id if isinstance(known, ApiKeyPrincipal) else None


def parse_api_key(authorization: str | None) -> ApiKeyToken:
    """The key of an Authorization header; 401 when there is none."""

    if authorization is None or not authorization.lower().startswith(BEARER_PREFIX):
        raise AuthenticationRequiredError(MISSING_KEY_MESSAGE)

    try:
        return ApiKeyToken(authorization[len(BEARER_PREFIX) :].strip())
    except BaseTypedStringConstraintViolationError as error:
        raise AuthenticationRequiredError(INVALID_KEY_MESSAGE) from error
