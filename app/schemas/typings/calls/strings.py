"""Keep abc order."""

from base_typed_string import BaseTypedString


class PbxCallDisposition(BaseTypedString):
    """
    How the telephony line says an incoming call ended, as it reported it
    (Zadarma: "answered", "busy", "cancel", "no answer", "failed", ...).
    """


# Keep abc order for all non example types, if possible.
