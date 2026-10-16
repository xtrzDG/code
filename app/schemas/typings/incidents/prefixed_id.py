"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class IncidentId(BasePrefixedTypedId):
    """Random identifier of one recorded incident (outage or data breach)."""

    prefix = "incident"


# Keep abc order for all non example types, if possible.
