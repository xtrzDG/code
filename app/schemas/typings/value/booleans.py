"""Keep abc order.

Example:
    is_weekly_digest_on: IsWeeklyDigestOn = True
"""

IsDailyDigestOn = bool
IsMonthlyReportOn = bool
# The value period starts on the day the business went live (or was
# created), later than the dates asked for.
IsPeriodSinceLaunch = bool
# The business's subscription is in its free trial.
IsTrialPeriod = bool
IsWeeklyDigestOn = bool
# Keep abc order for all non example types, if possible.
