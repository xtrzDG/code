"""Keep abc order."""

from base_typed_string import BaseTypedString


class ClientSummarySnapshot(BaseTypedString):
    """
    A client's summary for the platform admin as one refresh of the client
    standings computed it, kept as its JSON (the list reads it back as the
    summary of that moment and computes it again when it no longer reads).

    Example:
        snapshot = ClientSummarySnapshot('{"business_id": "business_..."}')
    """
