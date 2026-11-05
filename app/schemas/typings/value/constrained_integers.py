"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AverageCheckMinor(BaseConstrainedTypedInt):
    """
    What one booking (or order, for niches that take orders) brings a
    business on average, in minor units of the business currency.

    Example:
        average_check = AverageCheckMinor(12000)  # 120.00 GEL
    """

    ge = 0
    le = 100_000_000_000


class BookedValueMinor(BaseConstrainedTypedInt):
    """
    What bookings made in a period are worth by their own values (service
    prices, stays' nightly rates), summed in minor units of one currency.
    """

    ge = 0


class DigestRecipientCount(BaseConstrainedTypedInt):
    """How many people (e-mail addresses and devices) a report was queued for."""

    ge = 0


class EstimatedRevenueMinor(BaseConstrainedTypedInt):
    """
    Estimated money the assistant's bookings brought in a period (bookings
    times the average check), in minor units of the business currency.
    """

    ge = 0


class MonthlyPlanPriceMinor(BaseConstrainedTypedInt):
    """
    What a business's plan costs a month (an annual subscription spread over
    twelve months), in minor units of its currency; what a trial business
    pays once its free trial ends.

    Example:
        price = MonthlyPlanPriceMinor(51000)  # 510.00 GEL a month
    """

    ge = 0


class PlanCostMinor(BaseConstrainedTypedInt):
    """
    What a business's plan costs for the days of a value period, in minor
    units of its currency: the monthly price times the period's share of a
    month (the whole price for a calendar month).

    Example:
        plan_cost = PlanCostMinor(29900)  # 299.00 GEL
    """

    ge = 0


class StaffMinutesSaved(BaseConstrainedTypedInt):
    """Estimated minutes of staff work the assistant took over in a period."""

    ge = 0


class StaffSecondsPerCall(BaseConstrainedTypedInt):
    """Seconds of a staff member's time one answered phone call takes."""

    ge = 0
    le = 2 * 60 * 60


class StaffSecondsPerReply(BaseConstrainedTypedInt):
    """Seconds of a staff member's time one written reply to a customer takes."""

    ge = 0
    le = 60 * 60


# Keep abc order for all non example types, if possible.
