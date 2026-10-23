"""Closing a business: the owner's request, the cancellation and the banner's view."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.business_closures import (
    BusinessClosureReason,
    BusinessClosureState,
)
from app.schemas.typings.business_closures.booleans import (
    IsClosureCancellable,
    IsViewerBusinessOwner,
)
from app.schemas.typings.business_closures.constrained_strings import (
    BusinessNameConfirmation,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName


class CloseBusinessRequest(ImmutableDTO):
    """`POST /v1/businesses/{id}/closure`: the business's name, typed to confirm."""

    confirmation_name: BusinessNameConfirmation


class CloseBusinessCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    confirmation_name: BusinessNameConfirmation
    client_ip_address: ClientIpAddress | None = None


class CancelBusinessClosureCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    client_ip_address: ClientIpAddress | None = None


class BusinessClosureView(ImmutableDTO):
    """
    Where the business stands on its way out (the cabinet's countdown
    banner and Settings → Business's danger zone): ACTIVE without a closure;
    PENDING_DELETION with why, since when and until when (`delete_after`),
    who closed it, and whether this person may cancel it now (an owner, and
    for a closure for non-payment only once the subscription is paid
    again); DELETING once the deletion has begun.
    """

    business_id: BusinessId
    state: BusinessClosureState
    reason: BusinessClosureReason | None = None
    requested_at: Microseconds | None = None
    delete_after: Microseconds | None = None
    actor_name: UserDisplayName | None = None
    can_cancel: IsClosureCancellable = False
    viewer_is_owner: IsViewerBusinessOwner = False
