"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CancellationDetails(BaseConstrainedTypedString):
    """
    What an owner wrote in their own words when cancelling (optional, next
    to the reason they chose): one to a thousand characters, trimmed.

    Example:
        details = CancellationDetails("We close for the winter, back in May.")
    """

    min_length = 1
    max_length = 1000
    pattern = r"^\S(.*\S)?$"


# Keep abc order for all non example types, if possible.
