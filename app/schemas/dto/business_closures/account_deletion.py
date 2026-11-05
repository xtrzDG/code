"""`DELETE /v1/me`: a person deletes their own account."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId


class DeleteCurrentUserCommand(ImmutableDTO):
    user_id: UserId
    client_ip_address: ClientIpAddress | None = None
