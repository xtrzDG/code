"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class AccountCount(BaseConstrainedTypedInt):
    """Businesses paying for a subscription at a moment (accounts of ARPA)."""

    ge = 0


class MonthlyRecurringAmountMinor(BaseConstrainedTypedInt):
    """
    What a subscription brings in a month, in minor units of its currency:
    the monthly price, or the annual price spread over twelve months.

    Example:
        monthly = MonthlyRecurringAmountMinor(7900)  # 79.00 EUR
    """

    ge = 0


class OwnerCount(BaseConstrainedTypedInt):
    """Owners (people who signed up) in a funnel, cohort or tunnel step."""

    ge = 0


class TelemetryReportCount(BaseConstrainedTypedInt):
    """Reports of one kind a telemetry batch carried and the API kept."""

    ge = 0


class TimeToLiveSeconds(BaseConstrainedTypedInt):
    """Seconds from an owner's sign-up to their assistant first going live."""

    ge = 0


class TrialCount(BaseConstrainedTypedInt):
    """Free trials of businesses in a period (started, ended or converted)."""

    ge = 0


class WebVitalPercentile(BaseConstrainedTypedInt):
    """
    The 75th percentile of a Web Vital over many page views, in the
    vital's unit (milliseconds, or ten-thousandths of layout shift).
    """

    ge = 0
    le = 600_000


class WebVitalSampleCount(BaseConstrainedTypedInt):
    """Web Vital measurements behind a percentile."""

    ge = 0


class WebVitalValue(BaseConstrainedTypedInt):
    """
    One Web Vital measurement in the vital's unit: milliseconds for LCP and
    INP, ten-thousandths for CLS (a shift of 0.1 is 1000). Ten minutes is
    the most a page reports.

    Example:
        largest_paint = WebVitalValue(1840)
    """

    ge = 0
    le = 600_000


# Keep abc order for all non example types, if possible.
