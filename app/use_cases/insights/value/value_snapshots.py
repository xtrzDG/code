"""The totals of the value model as a report stores and shows them."""

from app.schemas.domain.value_reports import ValueReportDocument, ValueTotalsSnapshot
from app.schemas.dto.value.value_model import ValueTotals
from app.schemas.dto.value.value_reports import ValueReportView


def to_snapshot(totals: ValueTotals) -> ValueTotalsSnapshot:
    return ValueTotalsSnapshot.model_validate(totals.model_dump())


def from_snapshot(snapshot: ValueTotalsSnapshot) -> ValueTotals:
    return ValueTotals.model_validate(snapshot.model_dump())


def build_value_report_view(report: ValueReportDocument) -> ValueReportView:
    return ValueReportView(
        id=report.id,
        business_id=report.business_id,
        kind=report.kind,
        period_key=report.period_key,
        date_from=report.date_from,
        date_to=report.date_to,
        previous_date_from=report.previous_date_from,
        previous_date_to=report.previous_date_to,
        currency_code=report.currency_code,
        value_basis=report.value_basis,
        average_check_minor=report.average_check_minor,
        average_check_source=report.average_check_source,
        current=from_snapshot(report.current),
        previous=from_snapshot(report.previous),
        delivery=report.delivery,
        recipient_count=report.recipient_count,
        plan_cost_minor=report.plan_cost_minor,
        return_multiple=report.return_multiple,
        created_at=report.created_at,
    )
