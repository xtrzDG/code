"""
The admin team as the Team page shows it, the audit entry of a change,
and the rule that the team keeps a SUPER admin.
"""

from typed_time_provider import Microseconds

from app.contracts.platform_admins import PlatformAdminRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminTeamView, PlatformAdminView
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId

PLATFORM_ADMIN_ENTITY: AuditEntityName = AuditEntityName("platform_admin")
LAST_SUPER_MESSAGE: str = (
    "The admin team needs at least one SUPER admin: give the role to someone "
    "else first."
)


def team_view(
    platform_admin_repo: PlatformAdminRepoContract,
    user_repo: UserRepoContract,
    viewer_id: UserId,
) -> PlatformAdminTeamView:
    """SUPER admins first, then by when they were added."""

    admins: list[PlatformAdminDocument] = platform_admin_repo.list_team()
    adders: dict[UserId, UserDocument] = {
        user.id: user
        for user in user_repo.get_many(
            [admin.added_by for admin in admins if admin.added_by is not None]
        )
    }
    views: list[PlatformAdminView] = []
    for admin in admins:
        user: UserDocument | None = signed_in_user(user_repo, admin)
        adder: UserDocument | None = (
            adders.get(admin.added_by) if admin.added_by is not None else None
        )
        views.append(
            PlatformAdminView(
                id=admin.id,
                login_method=admin.login_method,
                phone_number=admin.phone_number,
                email=admin.email,
                role=admin.role,
                user_id=None if user is None else user.id,
                display_name=None if user is None else user.display_name,
                added_by=admin.added_by,
                added_by_name=None if adder is None else adder.display_name,
                created_at=admin.created_at,
                is_you=user is not None and user.id == viewer_id,
            )
        )
    views.sort(
        key=lambda view: (view.role is not PlatformAdminRole.SUPER, view.created_at)
    )
    return PlatformAdminTeamView(items=views)


def signed_in_user(
    user_repo: UserRepoContract, admin: PlatformAdminDocument
) -> UserDocument | None:
    """The account of the admin, once they have signed in."""

    if admin.login_method is LoginMethod.PHONE and admin.phone_number is not None:
        return user_repo.find_by_phone_number(admin.phone_number)

    if admin.email is not None:
        return user_repo.find_by_email(admin.email)

    return None


def refuse_losing_last_super(
    platform_admin_repo: PlatformAdminRepoContract,
    admin: PlatformAdminDocument,
    new_role: PlatformAdminRole | None,
) -> None:
    """ConflictError when the change leaves the team without a SUPER admin."""

    if admin.role is not PlatformAdminRole.SUPER or new_role is PlatformAdminRole.SUPER:
        return

    supers = platform_admin_repo.list_by_role(PlatformAdminRole.SUPER)
    if all(other.id == admin.id for other in supers):
        raise ConflictError(LAST_SUPER_MESSAGE)


def audit_team_change(
    audit_log_repo: AuditLogRepoContract,
    actor_id: UserId,
    admin: PlatformAdminDocument,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
    is_removed: bool = False,
) -> None:
    """
    PLATFORM_ADMIN_CHANGED: about the platform, it names no business. The
    entry names the record and its new role ("removed" when taken off).
    """

    change: str = "removed" if is_removed else admin.role.value
    audit_log_repo.append(
        AuditLogEntryDocument(
            actor_id=actor_id,
            action=AuditAction.PLATFORM_ADMIN_CHANGED,
            entity=PLATFORM_ADMIN_ENTITY,
            entity_id=AuditEntityReference(f"{admin.id}:{change}"),
            ip_address=client_ip_address,
            created_at=now,
            updated_at=now,
        )
    )
