"""The idempotency dependency built from the container's operators."""

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.idempotency.idempotency_dependency import (
    IdempotencyDependency,
    build_idempotency_dependency,
)
from app.gateways.http.user_authentication import CurrentUserDependency


def idempotency_of(
    operators: OperatorsContainer, current_user: CurrentUserDependency
) -> IdempotencyDependency:
    """The `Idempotency-Key` dependency of the creating routes."""

    return build_idempotency_dependency(
        current_user,
        operators.idempotency.claim_idempotency_key_operator(),
        operators.idempotency.finish_idempotent_request_operator(),
    )
