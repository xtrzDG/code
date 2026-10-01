"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CountryCallingCode(BaseConstrainedTypedInt):
    """
    International calling code of a country without the leading "+".

    Example:
        georgia_calling_code = CountryCallingCode(995)
    """

    ge = 1
    le = 999


# Keep abc order for all non example types, if possible.
