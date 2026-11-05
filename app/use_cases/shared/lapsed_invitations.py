"""
Team invitations of accounts that never signed in lapse after seven days
(OWASP ASVS V6.4.1): a phone number or e-mail that changes hands later
(a recycled number) must not land in the team. Nothing changes until the
invited person first signs in, since an account that never signed in has
no session; at that first sign-in every membership whose invitation lapsed
is removed, each audited as a DELETE of the `business_member`. An owner
may invite them again (a fresh invitation, InviteStaffUseCase). A business
whose only owner is the lapsed invitee (the inviting owner left since)
keeps them: a business always keeps an owner.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)

INVITATION_LIFETIME_MICROSECONDS: int = 7 * 24 * 60 * 60 * 1_000_000
MEMBER_ENTITY: AuditEntityName = AuditEntityName("business_member")


def is_invitation_lapsed(
    member: BusinessMember, user: UserDocument, now: Microseconds
) -> bool:
    """
    The member's invitation lapsed: the account never signed in and was
    invited seven days ago or more (an invitation from before `invited_at`
    counts from the account's creation, which it cannot predate).
    """

    if user.is_verified:
        return False

    invited_at: int = int(
        member.invited_at if member.invited_at is not None else user.created_at
    )
    return int(now) - invited_at >= INVITATION_LIFETIME_MICROSECONDS


class LapsedInvitations:
    """Removes the lapsed invitations of one person at their first sign-in."""

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def remove(self, user: UserDocument, now: Microseconds) -> list[BusinessId]:
        """The businesses `user` (not signed in yet) was taken out of."""

        if user.is_verified:
            return []

        removed: list[BusinessId] = []
        for business in self._business_repo.list_by_member(user.id):
            if not is_removable(business, user, now):
                continue

            def drop(current: BusinessDocument) -> None:
                if is_removable(current, user, now):
                    current.members = [
                        member
                        for member in current.members
                        if member.user_id != user.id
                    ]

            stored: BusinessDocument = self._business_repo.update(business.id, drop)
            if any(member.user_id == user.id for member in stored.members):
                # Invited again meanwhile (a fresh invitation): they stay.
                continue

            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=user.id,
                    action=AuditAction.DELETE,
                    entity=MEMBER_ENTITY,
                    entity_id=AuditEntityReference(str(user.id)),
                    created_at=now,
                    updated_at=now,
                )
            )
            removed.append(business.id)

        return removed


def is_removable(
    business: BusinessDocument, user: UserDocument, now: Microseconds
) -> bool:
    """The person's invitation lapsed and another owner stays."""

    is_lapsed: bool = any(
        member.user_id == user.id and is_invitation_lapsed(member, user, now)
        for member in business.members
    )
    return is_lapsed and any(
        member.user_id != user.id and member.role is BusinessMemberRole.OWNER
        for member in business.members
    )
