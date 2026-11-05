"""
Access of the signed-in user to the business named in a cabinet path.

Owners and staff pass; `required_role=OWNER` limits a route to owners. A
malformed business id is reported as a missing business.
"""

from typing import Protocol

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.operations.query_values import parse_path_id
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

BUSINESS_PREFIX: str = "/v1/businesses/{business_id}"


class BusinessAuthorizer(Protocol):
    """The business of a cabinet path, once the user's access is checked."""

    def __call__(
        self,
        user_id: UserId,
        raw_business_id: str,
        required_role: BusinessMemberRole | None = None,
    ) -> BusinessDocument: ...


def build_business_authorizer(
    authorize_business_access: OperatorContract[
        BusinessAccessRequest, BusinessDocument
    ],
) -> BusinessAuthorizer:
    """Authorizer that runs the access check operator for every route."""

    def authorize(
        user_id: UserId,
        raw_business_id: str,
        required_role: BusinessMemberRole | None = None,
    ) -> BusinessDocument:
        return authorize_business_access.operate(
            BusinessAccessRequest(
                user_id=user_id,
                business_id=parse_path_id(raw_business_id, BusinessId, "Business"),
                required_role=required_role,
            )
        )

    return authorize
