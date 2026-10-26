"""The closure's pure rules: an unpaid end, the typed name, the erase order."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.business_closures.constrained_strings import (
    BusinessNameConfirmation,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.businesses.closure.closure_rules import require_name_confirmation
from app.use_cases.businesses.closure.unpaid_ends import unpaid_end
from app.utilities.business_closures.retained_tables import (
    erase_order,
    ledger_erase_order,
)
from tests.storage.document_evolution.sample_documents import sample_document

DAY: int = 24 * 60 * 60 * 1_000_000
NOW: Microseconds = Microseconds(1_790_000_000_000_000)


def subscription(
    status: SubscriptionStatus,
    period_end: int = int(NOW) - DAY,
    grace_until: int | None = None,
) -> SubscriptionDocument:
    return sample_document(
        SubscriptionDocument, DocumentCollectionName("subscriptions")
    ).model_copy(
        update={
            "status": status,
            "period_end": Microseconds(period_end),
            "grace_until": None if grace_until is None else Microseconds(grace_until),
        }
    )


def paid_invoice(period_start: int, period_end: int) -> InvoiceDocument:
    return sample_document(
        InvoiceDocument, DocumentCollectionName("invoices")
    ).model_copy(
        update={
            "kind": InvoiceKind.SERVICE_PERIOD,
            "status": InvoiceStatus.PAID,
            "period_start": Microseconds(period_start),
            "period_end": Microseconds(period_end),
        }
    )


def test_a_missed_payment_ends_the_service_when_its_grace_runs_out() -> None:
    running = subscription(SubscriptionStatus.PAST_DUE, grace_until=int(NOW) + DAY)
    over = subscription(SubscriptionStatus.PAST_DUE, grace_until=int(NOW) - DAY)
    without_grace = subscription(SubscriptionStatus.PAST_DUE)

    assert unpaid_end(running, [], NOW) is None
    assert unpaid_end(over, [], NOW) == Microseconds(int(NOW) - DAY)
    assert unpaid_end(without_grace, [], NOW) is None


def test_a_cancelled_subscription_ends_after_the_last_period_paid_for() -> None:
    cancelled = subscription(SubscriptionStatus.CANCELLED, period_end=int(NOW) - DAY)
    paid_ahead = [paid_invoice(int(NOW) - DAY, int(NOW) + 5 * DAY)]
    paid_before = [paid_invoice(int(NOW) - 40 * DAY, int(NOW) - 10 * DAY)]
    later = subscription(SubscriptionStatus.CANCELLED, period_end=int(NOW) + DAY)

    assert unpaid_end(cancelled, [], NOW) == Microseconds(int(NOW) - DAY)
    assert unpaid_end(cancelled, paid_ahead, NOW) is None
    assert unpaid_end(cancelled, paid_before, NOW) == Microseconds(int(NOW) - DAY)
    assert unpaid_end(later, [], NOW) is None


@pytest.mark.parametrize(
    "status",
    [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING,
        SubscriptionStatus.INCOMPLETE,
        SubscriptionStatus.PAUSED,
    ],
)
def test_a_paid_or_never_paid_service_has_not_ended_unpaid(
    status: SubscriptionStatus,
) -> None:
    assert unpaid_end(subscription(status), [], NOW) is None
    assert unpaid_end(None, [], NOW) is None


def test_the_typed_name_matches_without_case_and_outer_spaces() -> None:
    business = sample_document(
        BusinessDocument, DocumentCollectionName("businesses")
    ).model_copy(update={"name": BusinessName("Mtsvane Ezo")})

    require_name_confirmation(business, BusinessNameConfirmation("  mtsvane ezo "))
    with pytest.raises(ValidationFailedError):
        require_name_confirmation(business, BusinessNameConfirmation("Mtsvane"))


def test_the_retained_tables_are_never_erased_and_the_business_goes_last() -> None:
    order = erase_order(
        [
            DocumentCollectionName(name)
            for name in ("businesses", "invoices", "contacts", "audit_log_entries")
        ]
    )

    assert [str(name) for name in order] == ["contacts", "businesses"]


def test_the_ledger_applied_again_keeps_the_job_queue() -> None:
    # The deletion's own sub-processor erasure jobs wait in the queue; the
    # ledger (the daily job, restore-check) never erases them.
    order = ledger_erase_order(
        [
            DocumentCollectionName(name)
            for name in ("businesses", "queued_jobs", "contacts", "invoices")
        ]
    )

    assert [str(name) for name in order] == ["contacts", "businesses"]
