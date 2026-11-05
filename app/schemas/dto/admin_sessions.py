"""A platform admin's view of a client team's sign-ins, and ending them."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import MaskedLoginDestination, UserDisplayName


class ClientMembersQuery(ImmutableDTO):
    """
    `user_id` is the platform admin asking, `client_id` the business. It
    is not `business_id`: people and their sessions are platform rows, so
    the operation runs outside any business's storage scope.
    """

    user_id: UserId
    client_id: BusinessId


class ClientMemberSessionsView(ImmutableDTO):
    """
    One member of a client's team: the role, the name and the masked phone
    or e-mail they sign in with, how many live sessions they have and when
    one was last used.
    """

    user_id: UserId
    role: BusinessMemberRole
    display_name: UserDisplayName | None = None
    masked_login: MaskedLoginDestination | None = None
    live_session_count: DocumentCount
    last_seen_at: Microseconds | None = None


class ClientMemberSessionList(ImmutableDTO):
    items: list[ClientMemberSessionsView]


class EndMemberSessionsCommand(ImmutableDTO):
    """
    A platform admin (`user_id`) ends every session of a member of the
    business `client_id` (platform rows: outside any business's scope).
    """

    user_id: UserId
    client_id: BusinessId
    member_user_id: UserId
    client_ip_address: ClientIpAddress | None = None
