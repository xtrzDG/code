"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class AuditLogEntryId(BasePrefixedTypedId):
    """Random identifier of one audit log entry."""

    prefix = "audit_log_entry"


class DpaAcceptanceId(BasePrefixedTypedId):
    """Random identifier of a data processing agreement acceptance."""

    prefix = "dpa_acceptance"


# Keep abc order for all non example types, if possible.
