"""
The providers the platform sends through: the name of each one's circuit
breaker, which provider carries a message, and which failures mean the
provider itself is in trouble (and so count against its circuit).
"""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    DeliveryNotConfiguredError,
    ExternalServiceError,
    ProviderCircuitOpenError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.exceptions.payment_errors import (
    PaymentProviderRefusedError,
    PaymentsNotConfiguredError,
)
from app.schemas.typings.platform.constrained_integers import WorkerLaneConcurrency
from app.schemas.typings.resilience.constrained_integers import ProviderSlotCount
from app.schemas.typings.resilience.constrained_strings import CircuitName

CIRCUIT_PREFIX: str = "provider"
# Providers with a circuit breaker; web push reaches many push services
# (one outage is not the others'), so it has none.
GUARDED_PROVIDERS: tuple[OutboundProvider, ...] = (
    OutboundProvider.META,
    OutboundProvider.TELEGRAM,
    OutboundProvider.PLATFORM_BOT,
    OutboundProvider.TWILIO_SMS,
    OutboundProvider.SMTP,
    OutboundProvider.FLITT,
    OutboundProvider.STRIPE,
    OutboundProvider.ELEVENLABS,
)
CUSTOMER_CHANNEL_PROVIDERS: dict[ChannelKind, OutboundProvider] = {
    ChannelKind.WHATSAPP: OutboundProvider.META,
    ChannelKind.MESSENGER: OutboundProvider.META,
    ChannelKind.INSTAGRAM: OutboundProvider.META,
    ChannelKind.TELEGRAM: OutboundProvider.TELEGRAM,
}
STAFF_CHANNEL_PROVIDERS: dict[ManagerContactChannel, OutboundProvider] = {
    ManagerContactChannel.TELEGRAM: OutboundProvider.PLATFORM_BOT,
    ManagerContactChannel.WHATSAPP: OutboundProvider.META,
    ManagerContactChannel.EMAIL: OutboundProvider.SMTP,
    ManagerContactChannel.SMS: OutboundProvider.TWILIO_SMS,
}
# The provider answered (a refusal, a pause it asked for, a setting to fix)
# or was never asked: none of these says it is down.
ANSWERED_FAILURES: tuple[type[ExternalServiceError], ...] = (
    ChannelCredentialRejectedError,
    DeliveryNotConfiguredError,
    PaymentProviderRefusedError,
    PaymentsNotConfiguredError,
    ProviderCircuitOpenError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
    WhatsAppTemplateRejectedError,
)


def provider_circuit(provider: OutboundProvider) -> CircuitName:
    """The circuit of a provider, e.g. "provider:meta"."""

    return CircuitName(f"{CIRCUIT_PREFIX}:{provider.value}")


def guarded_circuits() -> tuple[CircuitName, ...]:
    """Every provider circuit, listed from a process's start."""

    return tuple(provider_circuit(provider) for provider in GUARDED_PROVIDERS)


def is_provider_outage(error: ApplicationError) -> bool:
    """
    A failure that counts against the provider's circuit: a timeout, a
    connection error, a 5xx (an ExternalServiceError the provider did not
    answer with a refusal). A business's own setting that stopped the call
    before it left (missing credentials, an invalid target) says nothing
    about the provider.
    """

    return isinstance(error, ExternalServiceError) and not isinstance(
        error, ANSWERED_FAILURES
    )


def customer_channel_provider(channel: ChannelKind) -> OutboundProvider | None:
    """The provider of a customer channel (None: the platform carries it)."""

    return CUSTOMER_CHANNEL_PROVIDERS.get(channel)


def staff_channel_provider(channel: ManagerContactChannel) -> OutboundProvider:
    """The provider of a staff notification by the contact's channel."""

    return STAFF_CHANNEL_PROVIDERS[channel]


def provider_slots_of_lane(lane_threads: WorkerLaneConcurrency) -> ProviderSlotCount:
    """
    Each provider's share of a worker's outbound threads: half of them (2 of
    the default 4), at least one, so one provider that hangs leaves the
    other half to the rest.
    """

    return ProviderSlotCount(max(1, int(lane_threads) // 2))
