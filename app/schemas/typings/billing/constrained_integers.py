"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CurrencyMinorUnitDigits(BaseConstrainedTypedInt):
    """Number of minor-unit digits of a currency (EUR 2, JPY 0, KWD 3)."""

    ge = 0
    le = 4


class MoneyAmountMinor(BaseConstrainedTypedInt):
    """
    Non-negative money amount in minor units of its currency (cents, tetri).

    Example:
        voice_plan_price = MoneyAmountMinor(17500)  # 175.00 EUR
    """

    ge = 0


# Keep abc order for all non example types, if possible.
