"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ApiRequestsPerMinute(BaseConstrainedTypedInt):
    """
    How many API requests one caller may make in a sliding minute: a
    signed-in person (API_REQUESTS_PER_USER_PER_MINUTE, the exports'
    API_EXPORTS_PER_USER_PER_MINUTE) or one client address without a token
    (API_REQUESTS_PER_IP_PER_MINUTE).
    """

    ge = 1
    le = 1_000_000


class CallMaxDurationSeconds(BaseConstrainedTypedInt):
    """
    The longest phone call the voice agent keeps up (CALL_MAX_DURATION_SECONDS):
    the voice platform ends the call when it is reached.
    """

    ge = 60
    le = 7_200


class CallSilenceEndSeconds(BaseConstrainedTypedInt):
    """
    How long a caller may stay silent before the voice agent ends the call
    (CALL_SILENCE_END_SECONDS).
    """

    ge = 5
    le = 600


class DailySpendLimitMicroUsd(BaseConstrainedTypedInt):
    """
    A ceiling on one business's provider spend in one of its days, in
    millionths of a US dollar: past the soft one its assistant answers on
    a cheaper model, past the hard one it only takes messages for staff.

    Example:
        hard_limit = DailySpendLimitMicroUsd(15_000_000)  # $15 a day
    """

    ge = 0


class PlatformDailySpendBudgetMicroUsd(BaseConstrainedTypedInt):
    """
    The provider spend the whole platform plans for one UTC day
    (PLATFORM_DAILY_SPEND_BUDGET_USD), in millionths of a US dollar; the
    budget alert fires at 80 % of it.
    """

    ge = 1


class SpendLimitMultiple(BaseConstrainedTypedInt):
    """
    A daily spend limit as a multiple of the plan's planned daily provider
    cost (SPEND_SOFT_LIMIT_MULTIPLE, SPEND_HARD_LIMIT_MULTIPLE).
    """

    ge = 1
    le = 1_000


class SpendPercent(BaseConstrainedTypedInt):
    """Spend as a whole percentage of a limit or a budget (may pass 100)."""

    ge = 0
