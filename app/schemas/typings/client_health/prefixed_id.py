"""Keep abc order."""

from base_typed_id import BasePrefixedTypedId


class ClientHealthChangeId(BasePrefixedTypedId):
    """Random identifier of one change of a client's health status."""

    prefix = "client_health_change"


class ClientNoteId(BasePrefixedTypedId):
    """Random identifier of a platform admin's note about a client."""

    prefix = "client_note"


# Keep abc order for all non example types, if possible.
