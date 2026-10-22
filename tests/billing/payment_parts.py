"""The payment use cases of the billing testbed: checkout, webhooks, card on file."""

from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.billing.dunning_notice_facilitator import (
    DunningNoticeFacilitator,
)
from app.registries.billing.payment_provider_registry import PaymentProviderRegistry
from app.schemas.configurations.payment_settings import PaymentSettings
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.billing.card_on_file.get_payment_method_use_case import (
    GetPaymentMethodUseCase,
)
from app.use_cases.billing.card_on_file.retry_failed_payments_use_case import (
    RetryFailedPaymentsUseCase,
)
from app.use_cases.billing.card_on_file.start_card_setup_use_case import (
    StartCardSetupUseCase,
)
from app.use_cases.billing.issue_due_invoices_use_case import IssueDueInvoicesUseCase
from app.use_cases.billing.payment_webhook.apply_payment_status_use_case import (
    ApplyPaymentStatusUseCase,
)
from app.use_cases.billing.payment_webhook.process_payment_webhook_use_case import (
    ProcessPaymentWebhookUseCase,
)
from app.use_cases.billing.start_checkout_use_case import StartCheckoutUseCase
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.notifications.staff_link_signer import StaffLinkSigner
from tests.analytics.recording_product_events import RecordingProductEvents
from tests.billing.billing_infrastructure import BillingInfrastructure
from tests.billing.billing_settings import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from tests.foundation.access_support import ACCESS_SETTINGS


@dataclass
class PaymentParts:
    provider_registry: PaymentProviderRegistry
    start_checkout: StartCheckoutUseCase
    apply_payment_status: ApplyPaymentStatusUseCase
    process_webhook: ProcessPaymentWebhookUseCase
    get_payment_method: GetPaymentMethodUseCase
    start_card_setup: StartCardSetupUseCase
    dunning_notices: DunningNoticeFacilitator
    retry_failed_payments: RetryFailedPaymentsUseCase


def build_payment_parts(
    world: BillingInfrastructure,
    authorize: UseCaseContract[BusinessAccessRequest, BusinessDocument],
    issue_due_invoices: IssueDueInvoicesUseCase,
    product_events: RecordingProductEvents,
) -> PaymentParts:
    """The payment use cases over the testbed (Stripe configured)."""

    wall_clock: WallClock[Microseconds] = world.clock.wall_clock
    registry = PaymentProviderRegistry(
        PaymentSettings(
            stripe_secret_key=PlatformSecret(STRIPE_SECRET_KEY),
            stripe_webhook_secret=PlatformSecret(STRIPE_WEBHOOK_SECRET),
        )
    )
    apply_payment_status = ApplyPaymentStatusUseCase(
        payment_gateway=world.payment_gateway,
        subscription_repo=world.subscription_repo,
        invoice_repo=world.invoice_repo,
        business_repo=world.business_repo,
        user_repo=world.user_repo,
        plan_registry=world.plan_registry,
        issue_due_invoices=issue_due_invoices,
        manager_notifier=world.notifier,
        billing_notice_transformer=world.notice_transformer,
        wall_clock=wall_clock,
        referral_earnings=world.referral_earnings,
        payment_retry_repo=world.payment_retry_repo,
    )
    dunning_notices = DunningNoticeFacilitator(
        user_repo=world.user_repo,
        manager_notifier=world.notifier,
        link_signer=StaffLinkSigner(PlatformSecret("test-link-key-0000")),
        localized_text_resolver=LocalizedTextResolver(),
        app_settings=ACCESS_SETTINGS,
        wall_clock=wall_clock,
    )
    return PaymentParts(
        provider_registry=registry,
        start_checkout=StartCheckoutUseCase(
            authorize_business_access=authorize,
            subscription_repo=world.subscription_repo,
            invoice_repo=world.invoice_repo,
            payment_order_repo=world.payment_order_repo,
            issue_due_invoices=issue_due_invoices,
            payment_gateway=world.payment_gateway,
            app_settings=world.settings,
            wall_clock=wall_clock,
            invoice_issuing=world.invoicing.invoice_issuing,
            payment_provider_registry=registry,
        ),
        apply_payment_status=apply_payment_status,
        process_webhook=ProcessPaymentWebhookUseCase(
            payment_gateway=world.payment_gateway,
            payment_order_repo=world.payment_order_repo,
            subscription_repo=world.subscription_repo,
            business_repo=world.business_repo,
            apply_payment_status=apply_payment_status,
            secret_cipher=world.secret_cipher,
            wall_clock=wall_clock,
            product_events=product_events,
        ),
        get_payment_method=GetPaymentMethodUseCase(
            authorize_business_access=authorize,
            subscription_repo=world.subscription_repo,
            invoice_repo=world.invoice_repo,
            payment_retry_repo=world.payment_retry_repo,
            plan_registry=world.plan_registry,
            payment_provider_registry=registry,
            wall_clock=wall_clock,
        ),
        start_card_setup=StartCardSetupUseCase(
            authorize_business_access=authorize,
            subscription_repo=world.subscription_repo,
            invoice_repo=world.invoice_repo,
            payment_order_repo=world.payment_order_repo,
            payment_gateway=world.payment_gateway,
            payment_provider_registry=registry,
            invoice_issuing=world.invoicing.invoice_issuing,
            app_settings=world.settings,
            wall_clock=wall_clock,
        ),
        dunning_notices=dunning_notices,
        retry_failed_payments=RetryFailedPaymentsUseCase(
            business_repo=world.business_repo,
            subscription_repo=world.subscription_repo,
            invoice_repo=world.invoice_repo,
            payment_order_repo=world.payment_order_repo,
            payment_retry_repo=world.payment_retry_repo,
            plan_registry=world.plan_registry,
            payment_gateway=world.payment_gateway,
            secret_cipher=world.secret_cipher,
            dunning_notices=dunning_notices,
            wall_clock=wall_clock,
        ),
    )
