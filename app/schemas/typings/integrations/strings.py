"""Keep abc order."""

from base_typed_string import BaseTypedString


class WebhookPayloadJson(BaseTypedString):
    """
    The JSON body of one webhook event (the envelope with its data) as it
    is sent, byte for byte, on every attempt; the signature covers it.
    """


# Keep abc order for all non example types, if possible.
