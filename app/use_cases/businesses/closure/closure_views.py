"""The closure view of a business, as the banner and the danger zone show it."""

from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.business_closures import (
    BusinessClosureReason,
    BusinessClosureState,
)
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.business_closures.closure_views import BusinessClosureView
from app.schemas.typings.business_closures.booleans import IsViewerBusinessOwner
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.strings import UserDisplayName


def closure_view(
    business_id: BusinessId,
    closure: BusinessClosureDocument | None,
    user_repo: UserRepoContract,
    viewer_is_owner: IsViewerBusinessOwner,
    is_paid_again: bool,
) -> BusinessClosureView:
    """
    ACTIVE without a closure (or with one being cancelled);
    PENDING_DELETION until the deletion is queued,
    DELETING after. An owner may cancel a pending closure of their own
    kind, and one for non-payment once the service is paid for again.
    """

    if closure is None or closure.cancelled_at is not None:
        return BusinessClosureView(
            business_id=business_id,
            state=BusinessClosureState.ACTIVE,
            viewer_is_owner=viewer_is_owner,
        )

    state: BusinessClosureState = (
        BusinessClosureState.DELETING
        if closure.deletion_queued_at is not None
        else BusinessClosureState.PENDING_DELETION
    )
    may_cancel: bool = (
        viewer_is_owner
        and state is BusinessClosureState.PENDING_DELETION
        and (closure.reason is BusinessClosureReason.OWNER_REQUEST or is_paid_again)
    )
    return BusinessClosureView(
        business_id=business_id,
        state=state,
        reason=closure.reason,
        requested_at=closure.requested_at,
        delete_after=closure.delete_after,
        requested_by_name=requester_name(closure, user_repo),
        can_cancel=may_cancel,
        viewer_is_owner=viewer_is_owner,
    )


def requester_name(
    closure: BusinessClosureDocument, user_repo: UserRepoContract
) -> UserDisplayName | None:
    if closure.requested_by is None:
        return None

    user: UserDocument | None = user_repo.get(closure.requested_by)
    if user is None or user.display_name is None:
        return None

    return user.display_name
