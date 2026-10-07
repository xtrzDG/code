"""The `Idempotency-Key` dependency of creating routes."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from base_typed_string import BaseTypedStringConstraintViolationError
from fastapi import Depends, Header, Request
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.idempotency.idempotent_requests import (
    IDEMPOTENCY_KEY_HEADER,
    FinishIdempotentRequest,
    IdempotentReplay,
    PendingIdempotentRequest,
    slot_of,
)
from app.gateways.http.idempotency.request_fingerprint import fingerprint_request
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.idempotency import IdempotencyClaimVerdict
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.idempotency import (
    IdempotencyClaim,
    IdempotencyClaimDecision,
    IdempotentRequestOutcome,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.idempotency.constrained_strings import (
    IdempotencyKey,
    IdempotentOperation,
)
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId

type IdempotencyDependency = Callable[..., Coroutine[Any, Any, None]]
type RequestPartition = Callable[[Request], str]
type ClaimIdempotencyKeyOperator = OperatorContract[
    IdempotencyClaim, IdempotencyClaimDecision
]
type FinishIdempotentRequestOperator = OperatorContract[IdempotentRequestOutcome, None]

KEY_DESCRIPTION: str = (
    "Optional. A value you choose once per action (a UUID is best, at most "
    "255 visible ASCII characters) and send again on every retry of it. A "
    "retry gets the first answer back (with `Idempotent-Replayed: true`) "
    "instead of creating a second one; the same key with a different body "
    "is refused with 409 `idempotency_key_reused`, and a retry while the "
    "first request still runs with 409 `in_progress`. Keys are kept for 24 "
    "hours per user; a refused or failed request frees its key."
)
INVALID_KEY_MESSAGE: str = (
    "Idempotency-Key must be 1 to 255 visible ASCII characters (a UUID is best)."
)


def build_idempotency_dependency(
    current_user: CurrentUserDependency,
    claim_operator: ClaimIdempotencyKeyOperator,
    finish_operator: FinishIdempotentRequestOperator,
    partition: RequestPartition | None = None,
) -> IdempotencyDependency:
    """
    A dependency for creating routes, one line each:

        @router.post(..., dependencies=[Depends(idempotent)])

    Without the header the route runs as always. With it, the signed-in
    user's key is claimed before the route runs (after the bearer token is
    checked): a new key lets the route run and the response recorder keeps
    its answer; a retry of a request that succeeded gets that answer back;
    the 409 refusals come from the claim. The recorder
    (`install_idempotency`) must wrap the application. `partition` names
    what else a request's answer belongs to besides its user (the public
    API: the key it came with), read after `current_user` ran.
    """

    finish: FinishIdempotentRequest = finish_operator.operate

    async def claim_idempotency_key(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        idempotency_key: Annotated[
            str | None,
            Header(alias=IDEMPOTENCY_KEY_HEADER, description=KEY_DESCRIPTION),
        ] = None,
    ) -> None:
        if idempotency_key is None:
            return

        slot = slot_of(request.scope)
        if slot is None:
            raise RuntimeError(
                "Idempotency-Key needs install_idempotency on the application."
            )

        claim = IdempotencyClaim(
            user_id=user_id,
            key=parse_idempotency_key(idempotency_key),
            operation=operation_of(request),
            fingerprint=fingerprint_request(
                request.method,
                request.url.path,
                request.url.query,
                await request.body(),
                "" if partition is None else partition(request),
            ),
        )
        decision: IdempotencyClaimDecision = await run_in_threadpool(
            claim_operator.operate, claim
        )
        if (
            decision.verdict is IdempotencyClaimVerdict.REPLAY
            and decision.response is not None
        ):
            raise IdempotentReplay(decision.response)

        if decision.claim_id is not None:
            slot.pending = PendingIdempotentRequest(
                record_id=decision.record_id,
                claim_id=decision.claim_id,
                finish=finish,
            )

    return claim_idempotency_key


async def no_idempotency() -> None:
    """The default of router builders whose tests do not wire the keys."""


NO_IDEMPOTENCY: IdempotencyDependency = no_idempotency


def parse_idempotency_key(value: str) -> IdempotencyKey:
    """The header as a typed key; 422 `invalid` when it is not one."""

    try:
        return IdempotencyKey(value)
    except BaseTypedStringConstraintViolationError as error:
        raise ValidationFailedError(
            INVALID_KEY_MESSAGE,
            reasons=[
                ErrorReason(
                    code=ErrorReasonCode("invalid"),
                    message=ErrorReasonMessage(INVALID_KEY_MESSAGE),
                    details=[ErrorReasonDetail(f"header.{IDEMPOTENCY_KEY_HEADER}")],
                )
            ],
        ) from error


def operation_of(request: Request) -> IdempotentOperation:
    """The method and the route template the key is used for."""

    route: object = request.scope.get("route")
    template: str = route.path if isinstance(route, APIRoute) else request.url.path
    return IdempotentOperation(f"{request.method.upper()} {template}")
