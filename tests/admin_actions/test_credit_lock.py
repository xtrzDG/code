"""
Two invoices of one client issued at the same moment (a checkout and the
renewal job, in two processes) never spend the same credit: the balance is
read, the invoice stored and the used line written under the client's
credit lock.
"""

import threading
from collections import Counter

from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.schemas.constants.billing import BillingCreditKind
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.dto.billing_ledger import DueInvoicesRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.billing.issue_due_invoices_use_case import IssueDueInvoicesUseCase
from app.utilities.billing.billing_periods import add_billing_period
from tests.admin_actions.action_steps import credit
from tests.admin_actions.action_world import ActionWorld

# How long the first invoice, holding the lock with the balance read,
# waits for the second to read it too: without the lock it would.
SECOND_READER_WAIT_SECONDS: float = 0.3


class StallingLedger(BillingCreditRepoContract):
    """
    The ledger of the race: the first thread to read the balance a second
    time (inside the lock) waits for another thread's read before it
    writes, so without a lock both read the same balance.
    """

    def __init__(self, ledger: BillingCreditRepoContract) -> None:
        self._ledger: BillingCreditRepoContract = ledger
        self._reads: Counter[int] = Counter()
        self._guard = threading.Lock()
        self.first_locked_read = threading.Event()
        self.second_read = threading.Event()

    def record(self, line: BillingCreditDocument) -> bool:
        return self._ledger.record(line)

    def list_by_business(self, business_id: BusinessId) -> list[BillingCreditDocument]:
        thread: int = threading.get_ident()
        with self._guard:
            self._reads[thread] += 1
            is_locked_read = self._reads[thread] == 2
            is_first = is_locked_read and not self.first_locked_read.is_set()
            if is_locked_read and not is_first:
                self.second_read.set()
            if is_first:
                self.first_locked_read.set()

        lines = self._ledger.list_by_business(business_id)
        if is_first:
            self.second_read.wait(SECOND_READER_WAIT_SECONDS)
        return lines


def test_two_invoices_at_once_spend_the_credit_once() -> None:
    world = ActionWorld()
    credit(world, world.accountant)
    testbed = world.testbed
    ledger = StallingLedger(testbed.billing_credit_repo)
    issue = IssueDueInvoicesUseCase(
        invoice_repo=testbed.invoice_repo,
        plan_registry=testbed.plan_registry,
        invoice_description_transformer=testbed.invoice_description_transformer,
        wall_clock=testbed.clock.wall_clock,
        invoice_issuing=testbed.invoicing.invoice_issuing,
        invoice_line_texts_transformer=testbed.invoice_line_texts_transformer,
        billing_credit_repo=ledger,
        credit_lock=testbed.credit_lock,
    )
    subscription = testbed.subscription(world.business.id)
    business = world.client()
    first = subscription.period_end
    second = add_billing_period(first, subscription.billing_period, business.timezone)

    def run(period_start: object) -> None:
        issue.run(
            DueInvoicesRequest(
                business=business,
                subscription=subscription,
                period_start=period_start,  # type: ignore[arg-type]
            )
        )

    threads = [threading.Thread(target=run, args=(start,)) for start in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    used = [
        line
        for line in testbed.billing_credit_repo.list_by_business(world.business.id)
        if line.kind is BillingCreditKind.USED
    ]
    assert [int(line.amount_minor) for line in used] == [10_000]
    credited = [
        invoice
        for invoice in testbed.invoices(world.business.id)
        if invoice.credit_minor
    ]
    assert len(credited) == 1
    assert ledger.first_locked_read.is_set()
