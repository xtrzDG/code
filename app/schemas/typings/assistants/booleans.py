"""Keep abc order.

Example:
    is_autotest_passed: IsAutotestRunPassed = True
"""

AcceptsFailedAutotests = bool
CarriesBusinessChanges = bool
IsAutotestCaseActive = bool
IsAutotestRunPassed = bool
IsFullAutotestCoverage = bool
IsGoLiveCheckBlocking = bool
IsGoLiveCheckPassed = bool
IsReadyToGoLive = bool
# The assistant remembers returning customers (Settings → General).
RemembersCustomers = bool
# The team's internal notes on a customer's conversations reach the
# assistant's memory of them (off unless the owner turns it on).
SharesTeamNotesWithAssistant = bool
ShouldRunAutotests = bool
# Keep abc order for all non example types, if possible.
