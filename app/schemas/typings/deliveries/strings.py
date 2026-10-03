"""Keep abc order."""

from base_typed_string import BaseTypedString


class DeliveryErrorText(BaseTypedString):
    """
    Why the last send of an outbox message failed, as the platform said it
    (one line, no credentials).

    Example:
        error = DeliveryErrorText("Telegram sendMessage failed (502): Bad Gateway")
    """


class InboundErrorText(BaseTypedString):
    """
    Why the last processing of an inbox event failed.

    Example:
        error = InboundErrorText("The assistant of Funicular VR is not live.")
    """


class InboundPayloadText(BaseTypedString):
    """
    A verified webhook body kept in the inbox until the worker processes it
    (platform bot updates, finished-call reports). Never logged.
    """


# Keep abc order for all non example types, if possible.
