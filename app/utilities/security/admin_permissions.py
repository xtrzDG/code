"""What each platform admin role may do (least privilege, fixed in code)."""

from collections.abc import Mapping

from app.schemas.constants.access import PlatformAdminPermission, PlatformAdminRole

ROLE_PERMISSIONS: Mapping[PlatformAdminRole, frozenset[PlatformAdminPermission]] = {
    PlatformAdminRole.SUPER: frozenset(PlatformAdminPermission),
    # Helps clients: the client list, the platform's health and read-only
    # looks into a cabinet; never changes, money or the team.
    PlatformAdminRole.SUPPORT_READONLY: frozenset(
        {
            PlatformAdminPermission.VIEW_CLIENTS,
            PlatformAdminPermission.OPEN_CLIENT_CABINET,
            PlatformAdminPermission.VIEW_OPERATIONS,
        }
    ),
    # Money: the client list (with invoices and payments) and the growth
    # metrics; never a client's conversations.
    PlatformAdminRole.BILLING: frozenset(
        {
            PlatformAdminPermission.VIEW_CLIENTS,
            PlatformAdminPermission.VIEW_METRICS,
        }
    ),
}


def permissions_of(role: PlatformAdminRole | None) -> list[PlatformAdminPermission]:
    """The role's permissions in a stable order (none for no role)."""

    if role is None:
        return []

    granted: frozenset[PlatformAdminPermission] = ROLE_PERMISSIONS[role]
    return [
        permission for permission in PlatformAdminPermission if permission in granted
    ]


def has_permission(
    role: PlatformAdminRole | None, permission: PlatformAdminPermission
) -> bool:
    return role is not None and permission in ROLE_PERMISSIONS[role]
