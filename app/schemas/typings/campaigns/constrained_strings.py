"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CampaignMonthKey(BaseConstrainedTypedString):
    """
    The calendar month of a business's time zone a campaign message counts
    against ("2026-10"): the monthly cap counts the messages of one key.

    Example:
        month = CampaignMonthKey("2026-10")
    """

    min_length = 7
    max_length = 7
    pattern = r"^(19|20|21)[0-9]{2}-(0[1-9]|1[0-2])$"


# Keep abc order for all non example types, if possible.
