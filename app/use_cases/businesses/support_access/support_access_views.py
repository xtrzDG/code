"""The business's support access as its banner and settings show it."""

from typed_time_provider import Microseconds

from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.support_access import (
    SupportAccessView,
    SupportSessionView,
    SupportWriteAccessView,
)
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName
from app.use_cases.shared.support_access import (
    can_support_write,
    live_sessions,
    live_write_consent,
)

OWNERS_ONLY_MESSAGE: str = "Only the business's owners decide about support access."


def support_access_view(
    business: BusinessDocument,
    grants: list[SupportAccessGrantDocument],
    viewer_id: UserId,
    user_repo: UserRepoContract,
    platform_admins: PlatformAdminRegistryContract,
    now: Microseconds,
) -> SupportAccessView:
    """
    The open looks into the cabinet (newest first, with the admins' names),
    the owner's consent, and the viewer's own position.
    """

    sessions: list[SupportAccessGrantDocument] = sorted(
        live_sessions(grants, now), key=lambda grant: -int(grant.created_at)
    )
    admins: dict[UserId, UserDocument] = {
        user.id: user
        for user in user_repo.get_many(
            [grant.admin_user_id for grant in sessions if grant.admin_user_id]
        )
    }
    consent: SupportAccessGrantDocument | None = live_write_consent(grants, now)
    is_member: bool = any(member.user_id == viewer_id for member in business.members)
    viewer: UserDocument | None = None if is_member else user_repo.get(viewer_id)
    return SupportAccessView(
        sessions=[
            SupportSessionView(
                grant_id=grant.id,
                admin_name=_name(admins, grant.admin_user_id),
                reason=grant.reason,
                started_at=grant.created_at,
                expires_at=grant.expires_at,
                is_yours=grant.admin_user_id == viewer_id,
            )
            for grant in sessions
            if grant.reason is not None
        ],
        write_access=SupportWriteAccessView(
            is_allowed=consent is not None,
            expires_at=None if consent is None else consent.expires_at,
        ),
        is_support_viewer=not is_member,
        viewer_can_write=viewer is not None
        and can_support_write(platform_admins.role_of(viewer), grants, now),
    )


def require_owner_member(business: BusinessDocument, user_id: UserId) -> None:
    """
    Only an owner who is a member decides: platform support passes the
    owner-only reads of the access check, never these.
    """

    if not any(
        member.user_id == user_id and member.role is BusinessMemberRole.OWNER
        for member in business.members
    ):
        raise AccessDeniedError(OWNERS_ONLY_MESSAGE)


def _name(
    admins: dict[UserId, UserDocument], admin_id: UserId | None
) -> UserDisplayName | None:
    user: UserDocument | None = None if admin_id is None else admins.get(admin_id)
    return None if user is None else user.display_name
