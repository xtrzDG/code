"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CallOffsetSeconds(BaseConstrainedTypedInt):
    """
    Seconds from the start of a call to one line of its transcript.

    Example:
        offset = CallOffsetSeconds(42)
    """

    ge = 0


class DeliveredMessageCount(BaseConstrainedTypedInt):
    """
    Platform messages sent for one reply (long replies are split).

    Example:
        delivered = DeliveredMessageCount(2)
    """

    ge = 0
    le = 1000


class WidgetConfigStatusCode(BaseConstrainedTypedInt):
    """
    HTTP status of the failed chat configuration request the website widget
    reports through its error beacon.

    Example:
        status = WidgetConfigStatusCode(503)
    """

    ge = 100
    le = 599


class WidgetScriptPosition(BaseConstrainedTypedInt):
    """
    Line or column inside widget.js where a widget error was thrown, from
    the error's stack (the widget never sends the error message).

    Example:
        line = WidgetScriptPosition(1287)
    """

    ge = 0
    le = 10_000_000


class WebhookMessageCount(BaseConstrainedTypedInt):
    """
    Number of customer messages in one webhook delivery, by outcome.

    Example:
        answered = WebhookMessageCount(3)
    """

    ge = 0


# Keep abc order for all non example types, if possible.
