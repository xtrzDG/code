"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class CostMicroUsd(BaseConstrainedTypedInt):
    """
    Provider cost in millionths of a US dollar (no floating point money).

    Example:
        voice_minute_cost = CostMicroUsd(80_000)  # $0.08
    """

    ge = 0


class CurrencyMinorUnitDigits(BaseConstrainedTypedInt):
    """Number of minor-unit digits of a currency (EUR 2, JPY 0, KWD 3)."""

    ge = 0
    le = 4


class DiscountPercent(BaseConstrainedTypedInt):
    """Whole-number discount, e.g. 15 for the annual plan discount."""

    ge = 0
    le = 100


class GracePeriodDays(BaseConstrainedTypedInt):
    """Days a failed payment is tolerated before leads-only mode (concept: 7)."""

    ge = 0
    le = 90


class IncludedDialogs(BaseConstrainedTypedInt):
    """Text dialogs included in a plan package per month."""

    ge = 0


class IncludedVoiceMinutes(BaseConstrainedTypedInt):
    """Voice minutes included in a plan package per month."""

    ge = 0


class MoneyAmountMinor(BaseConstrainedTypedInt):
    """
    Non-negative money amount in minor units of its currency (cents, tetri).

    Example:
        voice_plan_price = MoneyAmountMinor(51700)  # 517.00 GEL
    """

    ge = 0


class TrialDays(BaseConstrainedTypedInt):
    """Length of the free trial (concept: 14 days)."""

    ge = 0
    le = 90


class UsageQuantity(BaseConstrainedTypedInt):
    """Quantity of one usage event in the unit of its UsageKind."""

    ge = 0


# Keep abc order for all non example types, if possible.
