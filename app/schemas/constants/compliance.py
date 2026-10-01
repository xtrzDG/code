from enum import StrEnum


class AuditAction(StrEnum):
    """
    Operation on personal data recorded in the audit log (concept section
    10), or a launch decision that must stay traceable (publishing a version
    that has not passed its autotests).
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
