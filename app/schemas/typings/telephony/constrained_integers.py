"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class PhoneNumberOfferCount(BaseConstrainedTypedInt):
    """
    How many available numbers one search shows the owner (1 to 20): enough
    to choose a memorable one, few enough to read on a phone.
    """

    ge = 1
    le = 20


class PhoneNumberPriceMarkupPercent(BaseConstrainedTypedInt):
    """
    What the platform adds to the carrier's monthly price of a number before
    it becomes the owner's price (0 to 300 percent; PHONE_NUMBER_PRICE_MARKUP_PERCENT).

    Example:
        markup = PhoneNumberPriceMarkupPercent(30)
    """

    ge = 0
    le = 300


class PhoneNumberRentalMinor(BaseConstrainedTypedInt):
    """
    What the owner pays a month for a number the platform rents for the
    business, in minor units of its currency (the carrier's price with the
    platform's markup, converted at the official rate and rounded up to a
    whole unit when the number is taken; fixed for the rental).

    Example:
        tbilisi_line = PhoneNumberRentalMinor(1200)  # 12.00 GEL a month
    """

    ge = 1
    le = 10_000_000


# Keep abc order for all non example types, if possible.
