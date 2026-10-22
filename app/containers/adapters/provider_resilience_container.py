from dependency_injector import containers
from dependency_injector.providers import (
    Callable,
    DependenciesContainer,
    Object,
    Singleton,
)

from app.adapters.notifications.circuit_breaking_telegram_bot_adapter import (
    CircuitBreakingTelegramBotAdapter,
)
from app.adapters.payments.circuit_breaking_payment_gateway_adapter import (
    CircuitBreakingPaymentGatewayAdapter,
)
from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.containers.adapters.provider_guards import (
    guard_email_sender,
    guard_sms_sender,
    outbound_provider_slots,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.messaging_clients import (
    EmailSenderClientContract,
    SmsMessagingClientContract,
)
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.facilitators.resilience.outbound_bulkhead_facilitator import (
    OutboundBulkheadFacilitator,
)
from app.schemas.constants.resilience import OutboundProvider
from app.utilities.resilience.provider_circuits import (
    guarded_circuits,
    provider_circuit,
)


class ProviderResilienceContainer(containers.DeclarativeContainer):
    """
    What stands between this process and its external providers: one
    circuit breaker per circuit for the whole process (the language models
    and every provider the platform sends through, `provider:*`), each
    provider's share of the outbound lane (half of its threads), and the
    platform's senders behind their circuits: the platform bot, SMTP,
    Twilio SMS and Flitt. Every worker writes the breakers' states into
    its pulse (GET /v1/admin/system).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    circuit_breaker: Singleton[CircuitBreakerFacilitator] = Singleton(
        CircuitBreakerFacilitator,
        monotonic_clock=time_provider.monotonic_clock,
        metrics=utilities.service_metrics,
        known_circuits=Callable(guarded_circuits),
    )
    outbound_bulkhead: Singleton[OutboundBulkheadFacilitator] = Singleton(
        OutboundBulkheadFacilitator,
        slots_per_provider=Callable(
            outbound_provider_slots, settings=config.app_settings
        ),
    )
    # The platform's Telegram bot (staff notifications, platform alerts):
    # its own circuit, apart from the businesses' bots.
    platform_bot_client: Singleton[CircuitBreakingTelegramBotAdapter] = Singleton(
        CircuitBreakingTelegramBotAdapter,
        inner_client=clients.telegram_bot_client,
        circuit_breaker=circuit_breaker,
        circuit=Object(provider_circuit(OutboundProvider.PLATFORM_BOT)),
    )
    email_sender: Singleton[EmailSenderClientContract | None] = Singleton(
        guard_email_sender,
        inner_client=clients.smtp_email_client,
        circuit_breaker=circuit_breaker,
    )
    sms_sender: Singleton[SmsMessagingClientContract | None] = Singleton(
        guard_sms_sender,
        inner_client=clients.twilio_messaging_client,
        circuit_breaker=circuit_breaker,
    )
    payment_gateway: Singleton[PaymentGatewayAdapterContract] = Singleton(
        CircuitBreakingPaymentGatewayAdapter,
        inner_adapter=Singleton(
            FlittPaymentGatewayAdapter,
            flitt_client=clients.flitt_client,
            app_base_url=config.app_settings.provided.app_base_url,
        ),
        circuit_breaker=circuit_breaker,
        circuit=Object(provider_circuit(OutboundProvider.FLITT)),
    )
