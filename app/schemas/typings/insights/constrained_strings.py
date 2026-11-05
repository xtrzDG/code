"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class TopicLabel(BaseConstrainedTypedString):
    """
    A short name of what customers ask about, as the nightly grouping of
    their first messages wrote it in the owner's language ("Prices of
    haircuts", "Parking"): 1 to 60 characters, not only whitespace.

    Example:
        label = TopicLabel("Opening hours")
    """

    min_length = 1
    max_length = 60
    pattern = r"\S"


# Keep abc order for all non example types, if possible.
