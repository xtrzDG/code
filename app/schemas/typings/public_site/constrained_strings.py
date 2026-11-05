"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class PublicDemoMessageText(BaseConstrainedTypedString):
    """
    What a visitor writes to a demo assistant on the landing page: one
    short message with at least one visible character (a real customer's
    question fits; a pasted document does not).

    Example:
        text = PublicDemoMessageText("Do you have a table for four tonight?")
    """

    min_length = 1
    max_length = 500
    pattern = r"\S"


class PublicDemoSessionKey(BaseConstrainedTypedString):
    """
    A visitor's demo conversation, chosen by the landing page (random, kept
    in the tab): one key is one conversation with one demo assistant.

    Example:
        key = PublicDemoSessionKey("k3v9Qe2LrT8sWm1Z")
    """

    pattern = r"^[A-Za-z0-9_-]{16,64}$"
