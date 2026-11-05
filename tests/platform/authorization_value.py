"""
A record of business B for the value operations of the matrix: a stored
monthly report (the demo stores none until the report job runs).
"""

from datetime import date
from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.value import ValueReportKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.value.constrained_strings import ValueReportPeriodKey
from app.use_cases.insights.value.value_access import value_model_query
from app.use_cases.insights.value.value_report_building import build_value_report
from app.utilities.value.value_periods import ReportPeriod, ValueDates, month_dates
from tests.e2e.harness import Workshop

REPORTED_MONTH: date = date(2026, 9, 1)


def value_path_values(
    workshop: Workshop,
    storage_scope: Any,
    business_id: str,
) -> dict[str, str]:
    """report_id: a monthly report of business B, stored as the job would."""

    container = workshop.container
    business_key = BusinessId(business_id)
    dates: ValueDates = month_dates(REPORTED_MONTH)
    period = ReportPeriod(
        kind=ValueReportKind.MONTHLY,
        period_key=ValueReportPeriodKey(REPORTED_MONTH.strftime("%Y-%m")),
        dates=dates,
    )
    with storage_scope.scoped_to_business(business_key):
        business: BusinessDocument | None = container.repositories.business_repo().get(
            business_key
        )
        assert business is not None
        model = container.use_cases.value.compute_value_model_use_case().run(
            value_model_query(business, dates)
        )
        report = build_value_report(
            business, period, model, Microseconds(0), business.created_at
        )
        assert container.repositories.value_report_repo().insert_if_new(report)

    return {"report_id": str(report.id)}
