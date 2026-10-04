from enum import StrEnum


class PlatformAdminRole(StrEnum):
    """
    What a platform admin is for. SUPER runs the platform: every admin
    page, the admin team, and, with the owner's consent, changes inside a
    client's cabinet. SUPPORT_READONLY helps clients: the client list, the
    platform's health, and time-boxed read-only looks into a client's
    cabinet. BILLING sees the client list and the growth metrics, never a
    client's conversations.
    """

    SUPER = "super"
    SUPPORT_READONLY = "support_readonly"
    BILLING = "billing"


class PlatformAdminPermission(StrEnum):
    """
    One thing an admin page or action needs; each role holds a fixed set
    (`app/utilities/security/admin_permissions.py`).
    """

    VIEW_CLIENTS = "view_clients"
    OPEN_CLIENT_CABINET = "open_client_cabinet"
    CHANGE_CLIENT_CABINET = "change_client_cabinet"
    VIEW_METRICS = "view_metrics"
    VIEW_OPERATIONS = "view_operations"
    MANAGE_OPERATIONS = "manage_operations"
    MANAGE_ADMINS = "manage_admins"


class SupportAccessKind(StrEnum):
    """
    A support access grant is either a platform admin's look into a
    client's cabinet (SESSION, an hour, read-only) or the owner's consent
    that support may also change things (WRITE_CONSENT, for the hours the
    owner chose).
    """

    SESSION = "session"
    WRITE_CONSENT = "write_consent"


class SupportAccessStatus(StrEnum):
    """OPEN until it ends: by time, by the admin, or by the owner."""

    OPEN = "open"
    ENDED = "ended"


class SupportAccessEndReason(StrEnum):
    """
    Why a grant ended: its time ran out (EXPIRED), the admin closed it
    (CLOSED_BY_ADMIN) or opened a new one in its place (REPLACED), or the
    owner ended it (REVOKED_BY_OWNER).
    """

    EXPIRED = "expired"
    CLOSED_BY_ADMIN = "closed_by_admin"
    REPLACED = "replaced"
    REVOKED_BY_OWNER = "revoked_by_owner"


class BusinessAccessMode(StrEnum):
    """
    What a request does to a business: READ (looking) or WRITE (changing,
    or copying personal data out, such as an export). The HTTP gateway
    reads it from the method (GET and HEAD read); a use case may ask for
    WRITE on a read, never the other way round. Platform support with a
    read-only grant may only READ.
    """

    READ = "read"
    WRITE = "write"
