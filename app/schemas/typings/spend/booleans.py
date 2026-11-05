"""Keep abc order."""

# A spend limit of the business's month, not of its day (the monthly hard
# stop on top of the daily limits).
IsMonthlySpendLimit = bool

# Every assistant of the platform hands customers to people (a platform
# admin's global pause).
IsPlatformPaused = bool
# The website chat of a business shows only on the websites it lists.
IsWidgetOriginRestricted = bool
