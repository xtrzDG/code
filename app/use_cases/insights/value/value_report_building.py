"""A stored report of a period from the value model, and whether to send it."""

from typed_time_provider import Microseconds

from app.schemas.constants.value import ValueReportDelivery
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.dto.value.value_model import ValueModel, ValueTotals
from app.schemas.typings.value.constrained_integers import DigestRecipientCount
from app.use_cases.insights.value.value_snapshots import to_snapshot
from app.utilities.value.value_keys import value_report_id_of
from app.utilities.value.value_periods import ReportPeriod


def build_value_report(
    business: BusinessDocument,
    period: ReportPeriod,
    model: ValueModel,
    starts_at: Microseconds,
    now: Microseconds,
) -> ValueReportDocument:
    """The report of the period, not sent yet (QUIET until it is)."""

    return ValueReportDocument(
        id=value_report_id_of(business.id, period.kind, period.period_key),
        business_id=business.id,
        kind=period.kind,
        period_key=period.period_key,
        date_from=model.date_from,
        date_to=model.date_to,
        previous_date_from=model.previous_date_from,
        previous_date_to=model.previous_date_to,
        starts_at=starts_at,
        currency_code=model.currency_code,
        value_basis=model.value_basis,
        average_check_minor=model.average_check_minor,
        average_check_source=model.average_check_source,
        current=to_snapshot(model.current),
        previous=to_snapshot(model.previous),
        delivery=ValueReportDelivery.QUIET,
        recipient_count=DigestRecipientCount(0),
        plan_cost_minor=model.plan_cost_minor,
        return_multiple=model.return_multiple,
        created_at=now,
        updated_at=now,
    )


def had_activity(totals: ValueTotals) -> bool:
    """Whether anything happened: a conversation, a booking or a request."""

    return (
        int(totals.conversation_count)
        + int(totals.booking_count)
        + int(totals.request_count)
        > 0
    )


def delivered(
    report: ValueReportDocument,
    recipients: DigestRecipientCount,
) -> ValueReportDocument:
    """The report as sent to `recipients` addresses and devices."""

    return report.model_copy(
        update={
            "delivery": (
                ValueReportDelivery.SENT
                if int(recipients) > 0
                else ValueReportDelivery.NO_RECIPIENTS
            ),
            "recipient_count": recipients,
        }
    )
