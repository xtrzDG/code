from functools import cached_property

from app.containers.payments.payment_dependencies import PaymentDependencies
from app.contracts.payment_declines import PaymentDeclineWatchFacilitatorContract
from app.contracts.payment_methods import (
    DunningNoticeFacilitatorContract,
    PaymentProviderRegistryContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.billing.dunning_notice_facilitator import (
    DunningNoticeFacilitator,
)
from app.facilitators.billing.payment_decline_watch_facilitator import (
    PaymentDeclineWatchFacilitator,
)
from app.registries.billing.payment_provider_registry import PaymentProviderRegistry
from app.schemas.constants.payments import PaymentWebhookOutcome
from app.schemas.dto.billing_cabinet import CheckoutSessionView, StartCheckoutCommand
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.dto.payment_methods import (
    CardSetupSessionView,
    PaymentMethodQuery,
    PaymentMethodView,
    StartCardSetupCommand,
)
from app.schemas.dto.payment_webhooks import PaymentStatusChange
from app.schemas.dto.payments import (
    PaymentWebhookDelivery,
    PaymentWebhookReceipt,
    VerifiedPaymentEvent,
)
from app.use_cases.billing.card_on_file.get_payment_method_use_case import (
    GetPaymentMethodUseCase,
)
from app.use_cases.billing.card_on_file.retry_failed_payments_use_case import (
    RetryFailedPaymentsUseCase,
)
from app.use_cases.billing.card_on_file.start_card_setup_use_case import (
    StartCardSetupUseCase,
)
from app.use_cases.billing.payment_webhook.apply_payment_event_use_case import (
    ApplyPaymentEventUseCase,
)
from app.use_cases.billing.payment_webhook.apply_payment_job_use_case import (
    ApplyPaymentJobUseCase,
)
from app.use_cases.billing.payment_webhook.apply_payment_status_use_case import (
    ApplyPaymentStatusUseCase,
)
from app.use_cases.billing.payment_webhook.receive_payment_webhook_use_case import (
    ReceivePaymentWebhookUseCase,
)
from app.use_cases.billing.start_checkout_use_case import StartCheckoutUseCase


class PaymentUseCaseFactories:
    """
    One typed factory per payments use case (R17-PAYMENTS-REGIONAL,
    migration 1214): checkout, the payment webhooks of both providers and
    the job that applies what they queued (API-03), the card on file
    ("Save card", "Update card") and the retries of declined automatic
    charges with the owners' notices. Each call builds a new use case; the
    registry of providers by country, the dunning notices and the watch
    over declined payments (LOG-05) are made once per root.
    """

    def __init__(self, dependencies: PaymentDependencies) -> None:
        self._dependencies: PaymentDependencies = dependencies

    @cached_property
    def payment_provider_registry(self) -> PaymentProviderRegistryContract:
        return PaymentProviderRegistry(
            payment_settings=self._dependencies.app_settings.payments
        )

    @cached_property
    def dunning_notices(self) -> DunningNoticeFacilitatorContract:
        given = self._dependencies
        return DunningNoticeFacilitator(
            user_repo=given.user_repo,
            manager_notifier=given.manager_notifier,
            link_signer=given.link_signer,
            localized_text_resolver=given.localized_text_resolver,
            app_settings=given.app_settings,
            wall_clock=given.wall_clock,
        )

    @cached_property
    def payment_declines(self) -> PaymentDeclineWatchFacilitatorContract:
        given = self._dependencies
        return PaymentDeclineWatchFacilitator(
            buckets=given.rate_limit_buckets,
            signal_counter=given.signal_counter,
            wall_clock=given.wall_clock,
        )

    def start_checkout(
        self,
    ) -> UseCaseContract[StartCheckoutCommand, CheckoutSessionView]:
        given = self._dependencies
        return StartCheckoutUseCase(
            authorize_business_access=given.authorize_business_access,
            subscription_repo=given.subscription_repo,
            invoice_repo=given.invoice_repo,
            payment_order_repo=given.payment_order_repo,
            issue_due_invoices=given.issue_due_invoices,
            payment_gateway=given.payment_gateway,
            app_settings=given.app_settings,
            wall_clock=given.wall_clock,
            invoice_issuing=given.invoice_issuing,
            payment_provider_registry=self.payment_provider_registry,
            payment_declines=self.payment_declines,
        )

    def apply_payment_status(
        self,
    ) -> UseCaseContract[PaymentStatusChange, PaymentWebhookOutcome]:
        given = self._dependencies
        return ApplyPaymentStatusUseCase(
            payment_gateway=given.payment_gateway,
            subscription_repo=given.subscription_repo,
            invoice_repo=given.invoice_repo,
            business_repo=given.business_repo,
            user_repo=given.user_repo,
            plan_registry=given.plan_registry,
            issue_due_invoices=given.issue_due_invoices,
            manager_notifier=given.manager_notifier,
            billing_notice_transformer=given.billing_notice_transformer,
            wall_clock=given.wall_clock,
            referral_earnings=given.referral_earnings,
            payment_retry_repo=given.payment_retry_repo,
            payment_order_repo=given.payment_order_repo,
        )

    def receive_payment_webhook(
        self,
    ) -> UseCaseContract[PaymentWebhookDelivery, PaymentWebhookReceipt]:
        given = self._dependencies
        return ReceivePaymentWebhookUseCase(
            payment_gateway=given.payment_gateway,
            payment_order_repo=given.payment_order_repo,
            job_queue=given.job_queue,
            secret_cipher=given.secret_cipher,
        )

    def apply_payment_event(
        self,
    ) -> UseCaseContract[VerifiedPaymentEvent, PaymentWebhookReceipt]:
        given = self._dependencies
        return ApplyPaymentEventUseCase(
            payment_gateway=given.payment_gateway,
            notification_lock=given.payment_notification_lock,
            payment_order_repo=given.payment_order_repo,
            subscription_repo=given.subscription_repo,
            business_repo=given.business_repo,
            apply_payment_status=self.apply_payment_status(),
            secret_cipher=given.secret_cipher,
            wall_clock=given.wall_clock,
            product_events=given.product_events,
            payment_declines=self.payment_declines,
        )

    def apply_payment_job(
        self,
    ) -> UseCaseContract[QueuedJobInput, PaymentWebhookReceipt]:
        return ApplyPaymentJobUseCase(
            apply_payment_event=self.apply_payment_event(),
            secret_cipher=self._dependencies.secret_cipher,
        )

    def get_payment_method(
        self,
    ) -> UseCaseContract[PaymentMethodQuery, PaymentMethodView]:
        given = self._dependencies
        return GetPaymentMethodUseCase(
            authorize_business_access=given.authorize_business_access,
            subscription_repo=given.subscription_repo,
            invoice_repo=given.invoice_repo,
            payment_retry_repo=given.payment_retry_repo,
            plan_registry=given.plan_registry,
            payment_provider_registry=self.payment_provider_registry,
            wall_clock=given.wall_clock,
            invoice_issuing=given.invoice_issuing,
            brand_repo=given.brand_repo,
            business_repo=given.business_repo,
        )

    def start_card_setup(
        self,
    ) -> UseCaseContract[StartCardSetupCommand, CardSetupSessionView]:
        given = self._dependencies
        return StartCardSetupUseCase(
            authorize_business_access=given.authorize_business_access,
            subscription_repo=given.subscription_repo,
            invoice_repo=given.invoice_repo,
            payment_order_repo=given.payment_order_repo,
            payment_gateway=given.payment_gateway,
            payment_provider_registry=self.payment_provider_registry,
            invoice_issuing=given.invoice_issuing,
            app_settings=given.app_settings,
            wall_clock=given.wall_clock,
            issue_due_invoices=given.issue_due_invoices,
            plan_registry=given.plan_registry,
            invoice_description_transformer=given.invoice_description_transformer,
            payment_declines=self.payment_declines,
        )

    def retry_failed_payments(self) -> UseCaseContract[JobTick, JobReport]:
        given = self._dependencies
        return RetryFailedPaymentsUseCase(
            business_repo=given.business_repo,
            subscription_repo=given.subscription_repo,
            invoice_repo=given.invoice_repo,
            payment_order_repo=given.payment_order_repo,
            payment_retry_repo=given.payment_retry_repo,
            plan_registry=given.plan_registry,
            payment_gateway=given.payment_gateway,
            secret_cipher=given.secret_cipher,
            dunning_notices=self.dunning_notices,
            wall_clock=given.wall_clock,
        )
