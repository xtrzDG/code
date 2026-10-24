"""
Localized templates of the owners' value digests (daily, weekly) and
monthly reports: what the assistant did and is worth, compared with the
period before, the link to the report and how to stop receiving it.
Counts follow "label: value" so no sentence needs plural forms.
"""

from collections.abc import Mapping

from app.schemas.constants.value import ValueBasis, ValueReportKind
from app.schemas.dto.localization import LocalizedText
from app.utilities.localization.owner_texts import owner_text

TITLES: Mapping[ValueReportKind, LocalizedText] = {
    ValueReportKind.DAILY: owner_text("notifications.value_digest.titles.daily"),
    ValueReportKind.WEEKLY: owner_text("notifications.value_digest.titles.weekly"),
    ValueReportKind.MONTHLY: owner_text("notifications.value_digest.titles.monthly"),
}
EARNINGS: Mapping[ValueBasis, LocalizedText] = {
    ValueBasis.BOOKINGS: owner_text("notifications.value_digest.earnings.bookings"),
    ValueBasis.REQUESTS: owner_text("notifications.value_digest.earnings.requests"),
}
MONEY: LocalizedText = owner_text("notifications.value_digest.money")
RETURN_SHORT: LocalizedText = owner_text("notifications.value_digest.return_short")
RETURN_ON_PLAN: LocalizedText = owner_text("notifications.value_digest.return_on_plan")
CHANGE_AGAINST: Mapping[ValueReportKind, LocalizedText] = {
    ValueReportKind.DAILY: owner_text(
        "notifications.value_digest.change_against.daily"
    ),
    ValueReportKind.WEEKLY: owner_text(
        "notifications.value_digest.change_against.weekly"
    ),
    ValueReportKind.MONTHLY: owner_text(
        "notifications.value_digest.change_against.monthly"
    ),
}
AFTER_HOURS: LocalizedText = owner_text("notifications.value_digest.after_hours")
TIME_SAVED: LocalizedText = owner_text("notifications.value_digest.time_saved")
HOURS: LocalizedText = owner_text("notifications.value_digest.hours")
MINUTES: LocalizedText = owner_text("notifications.value_digest.minutes")
OTHER_COUNTS: Mapping[ValueBasis, LocalizedText] = {
    ValueBasis.BOOKINGS: owner_text("notifications.value_digest.other_counts.bookings"),
    ValueBasis.REQUESTS: owner_text("notifications.value_digest.other_counts.requests"),
}
NO_CHECK_HINT: LocalizedText = owner_text("notifications.value_digest.no_check_hint")
TYPICAL_CHECK_HINT: LocalizedText = owner_text(
    "notifications.value_digest.typical_check_hint"
)
LINK_LINE: LocalizedText = owner_text("notifications.value_digest.link_line")
OPT_OUT: LocalizedText = owner_text("notifications.value_digest.opt_out")
