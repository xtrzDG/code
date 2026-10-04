from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.typings.access.booleans import IsSupportChangeAllowed
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId


class BusinessAccessRequest(ImmutableDTO):
    """
    Check that a signed-in user may act on a business.

    `required_role` OWNER limits the action to owners (billing, settings,
    publishing); None allows owners and staff. Platform support passes only
    during an open look into the cabinet (AuthorizeSupportAccessUseCase).
    `access_mode` WRITE marks a read that copies personal data out (an
    export); None takes the request's own (from its HTTP method).
    `support_may_change` marks an owner-only change platform support may
    make with the owner's consent: building and publishing the assistant
    (a done-for-you setup). Every other owner-only change (billing, team,
    channels, security, customers' data) stays the owner's alone.
    """

    user_id: UserId
    business_id: BusinessId
    required_role: BusinessMemberRole | None = None
    access_mode: BusinessAccessMode | None = None
    support_may_change: IsSupportChangeAllowed = False
