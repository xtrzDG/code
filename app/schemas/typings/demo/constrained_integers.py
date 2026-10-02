"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class DemoReplyPauseSeconds(BaseConstrainedTypedInt):
    """
    Seconds between a demo message and the one before it in its
    conversation (up to a day: a customer may come back the next morning).
    """

    ge = 0
    le = 86400
