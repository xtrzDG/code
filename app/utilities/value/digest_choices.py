"""Which summaries an owner wants (without stored choices: weekly and monthly)."""

from app.schemas.constants.value import ValueReportKind
from app.schemas.domain.value_settings import DigestPreferencesDocument


def wants_report(
    preferences: DigestPreferencesDocument | None,
    kind: ValueReportKind,
) -> bool:
    if preferences is None:
        return kind is not ValueReportKind.DAILY

    if kind is ValueReportKind.DAILY:
        return preferences.is_daily_digest_on

    if kind is ValueReportKind.WEEKLY:
        return preferences.is_weekly_digest_on

    return preferences.is_monthly_report_on
