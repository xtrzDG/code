"""
What stands between a process and its external providers, wired as plain
typed Python (ADR 0010) instead of a child container: one circuit breaker
per circuit for the whole process (the language models and every provider
the platform sends through, `provider:*`), each provider's share of the
outbound lane (half of its threads), and the platform's senders behind
their circuits: the platform bot, SMTP, Twilio SMS, and the payment
gateway that routes each call to Flitt or Stripe, each behind its own
circuit. Every worker
writes the breakers' states into its pulse (GET /v1/admin/system).

The provider graph holds one `Singleton` of `build_provider_resilience`
(AdaptersContainer.resilience) and exposes each part as a flat provider;
nothing here is silenced for the type checkers.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds, MonotonicClock, Nanoseconds, WallClock

from app.adapters.notifications.circuit_breaking_telegram_bot_adapter import (
    CircuitBreakingTelegramBotAdapter,
)
from app.adapters.payments.circuit_breaking_payment_gateway_adapter import (
    CircuitBreakingPaymentGatewayAdapter,
)
from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.adapters.payments.payment_gateway_router_adapter import (
    PaymentGatewayRouterAdapter,
)
from app.adapters.payments.stripe_billing_adapter import StripeBillingAdapter
from app.clients.flitt.flitt_client import FlittClient
from app.clients.stripe.stripe_client import StripeClient
from app.containers.adapters.provider_guards import (
    guard_email_sender,
    guard_sms_sender,
    outbound_provider_slots,
)
from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.messaging_clients import (
    EmailSenderClientContract,
    SmsMessagingClientContract,
)
from app.contracts.service_metrics import ServiceMetricsContract
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.facilitators.resilience.outbound_bulkhead_facilitator import (
    OutboundBulkheadFacilitator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.resilience import OutboundProvider
from app.utilities.resilience.provider_circuits import (
    guarded_circuits,
    provider_circuit,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderResilience:
    """The process's breakers, bulkheads and guarded platform senders."""

    circuit_breaker: CircuitBreakerFacilitator
    outbound_bulkhead: OutboundBulkheadFacilitator
    # The platform's Telegram bot (staff notifications, platform alerts):
    # its own circuit, apart from the businesses' bots.
    platform_bot_client: CircuitBreakingTelegramBotAdapter
    email_sender: EmailSenderClientContract | None
    sms_sender: SmsMessagingClientContract | None
    payment_gateway: PaymentGatewayAdapterContract


def build_provider_resilience(
    *,
    telegram_bot_client: TelegramBotApiClientContract,
    smtp_email_client: EmailSenderClientContract | None,
    twilio_messaging_client: SmsMessagingClientContract | None,
    flitt_client: FlittClient | None,
    stripe_client: StripeClient | None,
    settings: AppSettings,
    monotonic_clock: MonotonicClock[Nanoseconds],
    wall_clock: WallClock[Microseconds],
    metrics: ServiceMetricsContract,
) -> ProviderResilience:
    """Every part built once, around the one circuit breaker of the process."""

    circuit_breaker = CircuitBreakerFacilitator(
        monotonic_clock=monotonic_clock,
        metrics=metrics,
        known_circuits=guarded_circuits(),
    )
    return ProviderResilience(
        circuit_breaker=circuit_breaker,
        outbound_bulkhead=OutboundBulkheadFacilitator(
            slots_per_provider=outbound_provider_slots(settings)
        ),
        platform_bot_client=CircuitBreakingTelegramBotAdapter(
            inner_client=telegram_bot_client,
            circuit_breaker=circuit_breaker,
            circuit=provider_circuit(OutboundProvider.PLATFORM_BOT),
        ),
        email_sender=guard_email_sender(smtp_email_client, circuit_breaker),
        sms_sender=guard_sms_sender(twilio_messaging_client, circuit_breaker),
        # Payments: Flitt or Stripe by the provider each call names.
        payment_gateway=PaymentGatewayRouterAdapter(
            flitt_gateway=CircuitBreakingPaymentGatewayAdapter(
                inner_adapter=FlittPaymentGatewayAdapter(
                    flitt_client=flitt_client,
                    app_base_url=settings.app_base_url,
                    wall_clock=wall_clock,
                ),
                circuit_breaker=circuit_breaker,
                circuit=provider_circuit(OutboundProvider.FLITT),
            ),
            stripe_gateway=CircuitBreakingPaymentGatewayAdapter(
                inner_adapter=StripeBillingAdapter(
                    stripe_client=stripe_client,
                    cabinet_base_url=settings.cabinet_base_url,
                    wall_clock=wall_clock,
                ),
                circuit_breaker=circuit_breaker,
                circuit=provider_circuit(OutboundProvider.STRIPE),
            ),
        ),
    )
