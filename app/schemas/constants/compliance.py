from enum import StrEnum


class AuditAction(StrEnum):
    """
    Operation on personal data recorded in the audit log (concept section
    10), a launch decision that must stay traceable (publishing a version
    that has not passed its autotests), or a change of a person's
    two-factor sign-in (an authenticator added or removed, new recovery
    codes): MFA_CHANGED entries name no business. SUPPORT_ACCESS_START and
    SUPPORT_ACCESS_END bound a platform admin's time-boxed look into a
    client's cabinet (with the reason, the address and how it ended);
    SESSION_REVOKED (a person ended sessions of theirs) and
    PLATFORM_ADMIN_CHANGED (the admin team changed) name no business.
    """

    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    ADMIN_ACCESS = "admin_access"
    LOGIN = "login"
    RETENTION_PURGE = "retention_purge"
    PUBLISH_UNTESTED = "publish_untested"
    MFA_CHANGED = "mfa_changed"
    SUPPORT_ACCESS_START = "support_access_start"
    SUPPORT_ACCESS_END = "support_access_end"
    SESSION_REVOKED = "session_revoked"
    PLATFORM_ADMIN_CHANGED = "platform_admin_changed"
