import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.contracts.payment_methods import (
    DunningNoticeFacilitatorContract,
    PaymentRetryRepoContract,
)
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.billing.constrained_integers import PaymentRetryAttempt
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.billing.card_on_file.dunning_rules import (
    find_dunning_invoice,
    find_grace_start_of,
    find_schedule_order,
)
from app.use_cases.billing.card_on_file.payment_retry_run import PaymentRetryRun
from app.use_cases.shared.billing_records import (
    find_current_subscription,
    list_subscription_invoices,
)
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.billing.dunning_schedule import find_due_attempt

logger: logging.Logger = logging.getLogger(__name__)


class RetryFailedPaymentsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Background job (dunning): a declined automatic charge is charged again
    on days 1, 3 and 6 of the grace period, while the grace lasts.

    Each retry is claimed by inserting its row only if absent (its id
    derives from the invoice and the attempt), so it is charged once
    however many workers run the job; a retry missed while the job did
    not run is recorded as skipped and only the latest due one is made.
    Flitt charges the saved card's token, Stripe pays its own invoice
    again with the card on file. The owners hear about every declined
    retry (and the last one before the assistant only takes requests) and
    about the payment going through, by e-mail and in Telegram through the
    outbox. The provider's notice settles the invoice either way.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        payment_order_repo: PaymentOrderRepoContract,
        payment_retry_repo: PaymentRetryRepoContract,
        plan_registry: PlanRegistryContract,
        payment_gateway: PaymentGatewayAdapterContract,
        secret_cipher: SecretCipherAdapterContract,
        dunning_notices: DunningNoticeFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._payment_order_repo: PaymentOrderRepoContract = payment_order_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._run: PaymentRetryRun = PaymentRetryRun(
            payment_retry_repo=payment_retry_repo,
            payment_gateway=payment_gateway,
            secret_cipher=secret_cipher,
            dunning_notices=dunning_notices,
        )

    def run(self, input_data: JobTick) -> JobReport:
        processed: int = 0
        now: Microseconds = self._wall_clock.now_unix()
        for business in walk_businesses(self._business_repo):
            try:
                if self._retry_business(business, now):
                    processed += 1
            except Exception:
                # One business's failure never stops the others' retries.
                logger.exception("A payment retry failed for one business.")

        return JobReport(processed_count=ProcessedItemCount(processed))

    def _retry_business(self, business: BusinessDocument, now: Microseconds) -> bool:
        subscription: SubscriptionDocument | None = find_current_subscription(
            self._subscription_repo, business.id
        )
        if subscription is None or subscription.grace_until is None:
            return False

        invoices: list[InvoiceDocument] = list_subscription_invoices(
            self._invoice_repo, subscription
        )
        invoice: InvoiceDocument | None = find_dunning_invoice(subscription, invoices)
        grace_start = find_grace_start_of(self._plan_registry, subscription, business)
        if invoice is None or grace_start is None or now >= subscription.grace_until:
            return False

        attempt: PaymentRetryAttempt | None = find_due_attempt(
            grace_start, now, business.timezone
        )
        if attempt is None:
            return False

        schedule_order: PaymentOrderDocument | None = find_schedule_order(
            self._payment_order_repo, subscription
        )
        if schedule_order is None:
            return False

        claimed: PaymentRetryAttemptDocument | None = self._run.claim(
            business, subscription, invoice, schedule_order, attempt, grace_start, now
        )
        if claimed is None:
            return False

        self._run.charge(
            business, subscription, invoice, schedule_order, claimed, grace_start
        )
        return True
