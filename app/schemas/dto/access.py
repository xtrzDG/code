from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId


class BusinessAccessRequest(ImmutableDTO):
    """
    Check that a signed-in user may act on a business.

    `required_role` OWNER limits the action to owners (billing, settings,
    publishing); None allows owners and staff. Platform admins always pass
    and the access is written to the audit log.
    """

    user_id: UserId
    business_id: BusinessId
    required_role: BusinessMemberRole | None = None
