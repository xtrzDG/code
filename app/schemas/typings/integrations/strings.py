"""Keep abc order."""

from base_typed_string import BaseTypedString


class WebhookEndpointName(BaseTypedString):
    """
    How an endpoint is named to people (a notice that it was switched off):
    the owner's note for it, else the host of its address, never its path
    or query (they may hold the receiver's own secret).
    """


class WebhookPayloadJson(BaseTypedString):
    """
    The JSON body of one webhook event (the envelope with its data) as it
    is sent, byte for byte, on every attempt; the signature covers it.
    """


# Keep abc order for all non example types, if possible.
