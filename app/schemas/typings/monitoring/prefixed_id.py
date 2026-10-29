"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class MaintenanceRunId(BasePrefixedTypedId):
    """Random identifier of one recorded backup or restore drill."""

    prefix = "maintenance_run"


# Keep abc order for all non example types, if possible.
