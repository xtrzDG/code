from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.admin_actions import AdminActionReceipt, OverridePlanCommand
from app.schemas.dto.billing import Money
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.admin.billing_actions.account_action_gate import (
    SUBSCRIPTION_ENTITY,
    AccountActionGate,
    AccountActionTarget,
    AdminActionRecord,
)
from app.use_cases.shared.billing_records import (
    list_open_invoices,
    list_subscription_invoices,
)
from app.use_cases.shared.subscription_pricing import price_subscription
from app.utilities.analytics.billing_event_drafts import billing_event


class OverridePlanUseCase(UseCaseContract[OverridePlanCommand, AdminActionReceipt]):
    """
    POST /v1/admin/clients/{business_id}/plan: the platform team sets the
    client's plan (and billing period) by hand, without a checkout, at the
    price book's price in the subscription's currency, from the next bill.

    As when the owner changes plans: when what is charged changes, the
    automatic charges stop (the provider would keep charging the old
    amount; the owner pays the next bill in the cabinet, which starts them
    again) and the unpaid bills of the old price are voided; a plan without
    voice takes the voice agent down. The audit log keeps the admin's
    reason (ADMIN_PLAN_OVERRIDDEN); growth metrics get PLAN_CHANGED.

    Raises:
        ConflictError: the client is on that plan and period already.
        ValidationFailedError: the plan has no price in the currency.
    """

    def __init__(
        self,
        gate: AccountActionGate,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        business_repo: BusinessRepoContract,
        plan_registry: PlanRegistryContract,
        payment_gateway: PaymentGatewayAdapterContract,
        remove_voice_agent: UseCaseContract[BusinessId, None],
        product_events: RecordProductEventFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._gate: AccountActionGate = gate
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._payment_gateway: PaymentGatewayAdapterContract = payment_gateway
        self._remove_voice_agent: UseCaseContract[BusinessId, None] = remove_voice_agent
        self._product_events: RecordProductEventFacilitatorContract = product_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: OverridePlanCommand) -> AdminActionReceipt:
        target: AccountActionTarget = self._gate.admit(
            input_data.user_id, input_data.business_id
        )
        subscription: SubscriptionDocument = target.subscription
        plan_key: PlanKey = input_data.body.plan_key
        period: BillingPeriod = (
            input_data.body.billing_period or subscription.billing_period
        )
        if plan_key is subscription.plan_key and period is subscription.billing_period:
            raise ConflictError("The client is on this plan already.")

        price: Money = price_subscription(
            self._plan_registry, plan_key, period, subscription.currency_code
        )
        now: Microseconds = self._wall_clock.now_unix()
        is_charge_changed: bool = (
            price.amount_minor != subscription.price_minor
            or period is not subscription.billing_period
        )
        previous_plan_key: PlanKey = subscription.plan_key
        with self._gate.transaction():
            if is_charge_changed:
                self._void_old_price_bills(subscription, now)

            subscription.plan_key = plan_key
            subscription.billing_period = period
            subscription.price_minor = price.amount_minor
            subscription.updated_at = now
            self._subscription_repo.save(subscription)
            self._business_repo.update(
                target.business.id, lambda current: set_plan(current, plan_key, now)
            )
            receipt: AdminActionReceipt = self._gate.record(
                target,
                AdminActionRecord(
                    action=AuditAction.ADMIN_PLAN_OVERRIDDEN,
                    entity=SUBSCRIPTION_ENTITY,
                    entity_id=str(subscription.id),
                    reason=input_data.body.reason,
                    client_ip_address=input_data.client_ip_address,
                ),
                now,
            )

        reference = subscription.provider_reference
        if is_charge_changed and reference is not None:
            self._payment_gateway.stop_recurring(reference)
            subscription.provider_reference = None
            self._subscription_repo.save(subscription)

        self._product_events.record(
            billing_event(
                ProductEventName.PLAN_CHANGED,
                subscription,
                target.admin.id,
                previous_plan_key,
            )
        )
        if not self._plan_registry.get(plan_key).is_voice_included:
            self._remove_voice_agent.run(target.business.id)

        return receipt

    def _void_old_price_bills(
        self, subscription: SubscriptionDocument, now: Microseconds
    ) -> None:
        for invoice in list_open_invoices(
            list_subscription_invoices(self._invoice_repo, subscription)
        ):
            if invoice.kind is InvoiceKind.SERVICE_PERIOD:
                invoice.status = InvoiceStatus.VOID
                invoice.updated_at = now
                self._invoice_repo.save(invoice)


def set_plan(business: BusinessDocument, plan_key: PlanKey, now: Microseconds) -> None:
    """The business's own plan, as stored now (an edit saved meanwhile stays)."""

    business.plan_key = plan_key
    business.updated_at = now
