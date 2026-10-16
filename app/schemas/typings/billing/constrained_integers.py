"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class BillingCreditAmountMinor(BaseConstrainedTypedInt):
    """
    Credit of one ledger line in minor units of its currency: at least one
    minor unit and at most 100 000.00 (a grant is a goodwill gesture, never
    a fortune).

    Example:
        two_months_free = BillingCreditAmountMinor(103400)  # 1 034.00 GEL
    """

    ge = 1
    le = 10_000_000


class BillingIntervalMonths(BaseConstrainedTypedInt):
    """
    Months between two automatic charges of a subscription (1 or 12).

    Example:
        annual_interval = BillingIntervalMonths(12)
    """

    ge = 1
    le = 12


class ClientDiscountPercent(BaseConstrainedTypedInt):
    """
    Whole-number discount a platform admin gave one client on its service
    periods (1 to 100; 100 is a free period).

    Example:
        launch_deal = ClientDiscountPercent(30)
    """

    ge = 1
    le = 100


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


class ExchangeRateDayNumber(BaseConstrainedTypedInt):
    """
    The calendar day a rate was set for as the number YYYYMMDD, so the
    newest rate of a pair is found by an index.

    Example:
        nbg_rate_day = ExchangeRateDayNumber(20260930)
    """

    ge = 19700101
    le = 99991231


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


class OverageVoiceMinutes(BaseConstrainedTypedInt):
    """Voice minutes used above the package of a plan in one period."""

    ge = 0


class PackageUsagePercent(BaseConstrainedTypedInt):
    """
    Whole percent of an included package used in one period (may exceed 100).

    Example:
        minutes_share = PackageUsagePercent(82)
    """

    ge = 0


class TrialDays(BaseConstrainedTypedInt):
    """Length of the free trial (concept: 14 days)."""

    ge = 0
    le = 90


class TrialExtensionDays(BaseConstrainedTypedInt):
    """
    Days a platform admin adds to a client's free trial at once (a slow
    onboarding gets a week or two more).

    Example:
        one_more_week = TrialExtensionDays(7)
    """

    ge = 1
    le = 60


class UsageQuantity(BaseConstrainedTypedInt):
    """Quantity of one usage event in the unit of its UsageKind."""

    ge = 0


class UsageQuantityTotal(BaseConstrainedTypedInt):
    """Sum of the quantities of one UsageKind over a period."""

    ge = 0


class UsedDialogs(BaseConstrainedTypedInt):
    """Text dialogs started in one billing period."""

    ge = 0


class UsedVoiceMinutes(BaseConstrainedTypedInt):
    """Voice minutes used in one billing period, rounded up to whole minutes."""

    ge = 0


# Keep abc order for all non example types, if possible.
