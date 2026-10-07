"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class PublicDemoMessagesLeft(BaseConstrainedTypedInt):
    """
    Messages one visitor may still send to a demo assistant in the current
    hour (the landing page shows it once few are left).
    """

    ge = 0
    le = 1_000


class PublicDemoMessagesPerHour(BaseConstrainedTypedInt):
    """
    Messages every visitor of the landing page together may send to the
    demo assistants in one hour (PUBLIC_DEMO_MESSAGES_PER_HOUR): the bound
    of the model spend the public demo can cause.
    """

    ge = 1
    le = 100_000
