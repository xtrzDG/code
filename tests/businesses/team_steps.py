"""Steps of the team tests: invite and remove members."""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.businesses import (
    BusinessView,
    InviteStaffCommand,
    InviteStaffRequest,
    RemoveMemberCommand,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId
from tests.users.accounts_testbed import AccountsTestbed


def invite(
    testbed: AccountsTestbed,
    owner_id: UserId,
    business: BusinessDocument,
    invitation: InviteStaffRequest,
) -> BusinessView:
    return testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=owner_id,
            business_id=business.id,
            invitation=invitation,
            client_ip_address=ClientIpAddress("198.51.100.4"),
        )
    )


def remove(
    testbed: AccountsTestbed,
    actor_id: UserId,
    business: BusinessDocument,
    member_id: UserId,
) -> BusinessView:
    return testbed.remove_member.run(
        RemoveMemberCommand(
            user_id=actor_id,
            business_id=business.id,
            member_user_id=member_id,
        )
    )
