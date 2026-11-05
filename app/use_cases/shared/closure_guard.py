"""
A closing business stays closed: while a closure waits for its deletion
(not cancelled), nothing makes the business live again or turns a channel
on. Only cancelling the closure brings them back (`ClosureEffects.restore`,
which runs after the closure is marked cancelled).
"""

from app.contracts.repositories.business_closure_repositories import (
    BusinessClosureRepoContract,
)
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId


def is_closing(
    closure_repo: BusinessClosureRepoContract | None, business_id: BusinessId
) -> bool:
    if closure_repo is None:
        return False

    closure: BusinessClosureDocument | None = closure_repo.get(business_id)
    return closure is not None and closure.cancelled_at is None


def refuse_while_closing(
    closure_repo: BusinessClosureRepoContract | None,
    business_id: BusinessId,
    what: str,
) -> None:
    """ConflictError when the business is closing; `what` names the refused step."""

    if is_closing(closure_repo, business_id):
        raise ConflictError(
            f"The business is closing: cancel the closure in Settings → "
            f"Business to {what}."
        )
