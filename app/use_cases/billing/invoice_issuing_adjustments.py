"""
The discount and the credit of an invoice the platform issues to be paid:
worked out from the subscription and the business's ledger, under the
business's credit lock when it has credit to use.
"""

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager, nullcontext

from typed_time_provider import Microseconds

from app.contracts.billing_credits import BillingCreditLockRegistryContract
from app.contracts.repositories.billing_repositories import InvoiceRepoContract
from app.contracts.repositories.client_care_repositories import (
    BillingCreditRepoContract,
)
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.billing import InvoiceStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.utilities.billing.billing_credit_ledger import credit_balance, used_credit_line
from app.utilities.billing.invoice_adjustments import (
    PriceAdjustment,
    adjust_price,
    discount_for_period,
)

type IssueAdjusted = Callable[[InvoiceDocument], InvoiceDocument]


class InvoiceIssuingAdjustments:
    """
    Issue a draft invoice with what comes off its price before tax: the
    client's discount (service periods only), then the credit it has in the
    invoice's currency. With credit, the balance is read, the invoice
    stored and the used line written while the business's credit lock is
    held, so two invoices issued at once never spend the same credit.

    The lock's transaction is the platform's (`platform_wide()`), and the
    block runs in the business's scope inside it: numbering the invoice
    takes the platform-wide counter (`invoice_counters`), which the tenant
    database role may not touch (migration 1200), so the unit of work of a
    business's scope could never number an invoice with credit.
    """

    def __init__(
        self,
        invoice_repo: InvoiceRepoContract,
        billing_credit_repo: BillingCreditRepoContract,
        credit_lock: BillingCreditLockRegistryContract,
        storage_scope: StorageScopeContract,
    ) -> None:
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._billing_credit_repo: BillingCreditRepoContract = billing_credit_repo
        self._credit_lock: BillingCreditLockRegistryContract = credit_lock
        self._storage_scope: StorageScopeContract = storage_scope

    def issue(
        self,
        subscription: SubscriptionDocument,
        draft: InvoiceDocument,
        issue_and_store: IssueAdjusted,
        now: Microseconds,
    ) -> InvoiceDocument:
        """
        `issue_and_store` numbers the adjusted draft, adds the VAT, gives it
        its status and stores it; the used credit's line follows.
        """

        has_credit: bool = self._available(draft) > 0
        lock: AbstractContextManager[object] = (
            self._credit_held(draft) if has_credit else nullcontext()
        )
        with lock:
            adjustment: PriceAdjustment = adjust_price(
                int(draft.amount_minor),
                discount_for_period(subscription, draft.kind, draft.period_start),
                self._available(draft) if has_credit else 0,
            )
            invoice: InvoiceDocument = issue_and_store(adjusted(draft, adjustment))
            if adjustment.credit_minor > 0:
                self._billing_credit_repo.record(
                    used_credit_line(invoice, adjustment.credit_minor, now)
                )

            return invoice

    @contextmanager
    def _credit_held(self, draft: InvoiceDocument) -> Generator[object]:
        """The credit lock in a platform transaction, the block in the business."""

        with (
            self._storage_scope.platform_wide(),
            self._credit_lock.lock_for(draft.business_id),
            self._storage_scope.scoped_to_business(draft.business_id) as scope,
        ):
            yield scope

    def _available(self, draft: InvoiceDocument) -> int:
        lines = self._billing_credit_repo.list_by_business(draft.business_id)
        if not lines:
            return 0

        return credit_balance(
            lines,
            self._invoice_repo.list_by_business(draft.business_id),
            draft.currency_code,
        )


def adjusted(draft: InvoiceDocument, adjustment: PriceAdjustment) -> InvoiceDocument:
    """The draft priced at its subtotal, naming its discount and credit."""

    if adjustment.discount_minor == 0 and adjustment.credit_minor == 0:
        return draft

    return draft.model_copy(
        update={
            "amount_minor": MoneyAmountMinor(adjustment.subtotal_minor),
            "discount_percent": adjustment.discount_percent,
            "discount_minor": (
                MoneyAmountMinor(adjustment.discount_minor)
                if adjustment.discount_minor
                else None
            ),
            "credit_minor": (
                MoneyAmountMinor(adjustment.credit_minor)
                if adjustment.credit_minor
                else None
            ),
        }
    )


def settled_status(requested: InvoiceStatus, invoice: InvoiceDocument) -> InvoiceStatus:
    """A bill to pay that a discount or credit brought to zero is paid."""

    if (
        requested is InvoiceStatus.ISSUED
        and int(invoice.amount_minor) == 0
        and (invoice.discount_minor is not None or invoice.credit_minor is not None)
    ):
        return InvoiceStatus.PAID

    return requested
