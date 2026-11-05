"""
The guarded senders of the provider resilience: a provider's client behind
its circuit breaker, or None while the provider is not configured (as the
client itself); a business's SMS behind its hourly volume too.
"""

from typed_time_provider import Microseconds, WallClock

from app.adapters.monitoring.bucket_signal_counter_adapter import (
    BucketSignalCounterAdapter,
)
from app.adapters.notifications.circuit_breaking_email_sender_adapter import (
    CircuitBreakingEmailSenderAdapter,
)
from app.adapters.notifications.circuit_breaking_sms_sender_adapter import (
    CircuitBreakingSmsSenderAdapter,
)
from app.adapters.notifications.tenant_sms_volume_guard_adapter import (
    TenantSmsVolumeGuardAdapter,
)
from app.contracts.messaging_clients import (
    EmailSenderClientContract,
    SmsMessagingClientContract,
)
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.typings.platform.constrained_integers import WorkerLaneConcurrency
from app.schemas.typings.resilience.constrained_integers import ProviderSlotCount
from app.utilities.resilience.provider_circuits import (
    provider_circuit,
    provider_slots_of_lane,
)

DEFAULT_OUTBOUND_THREADS: WorkerLaneConcurrency = WorkerLaneConcurrency(4)


def guard_email_sender(
    inner_client: EmailSenderClientContract | None,
    circuit_breaker: CircuitBreakerContract,
) -> EmailSenderClientContract | None:
    if inner_client is None:
        return None

    return CircuitBreakingEmailSenderAdapter(
        inner_client, circuit_breaker, provider_circuit(OutboundProvider.SMTP)
    )


def guard_sms_sender(
    inner_client: SmsMessagingClientContract | None,
    circuit_breaker: CircuitBreakerContract,
) -> SmsMessagingClientContract | None:
    if inner_client is None:
        return None

    return CircuitBreakingSmsSenderAdapter(
        inner_client, circuit_breaker, provider_circuit(OutboundProvider.TWILIO_SMS)
    )


def guard_tenant_sms_volume(
    inner_client: SmsMessagingClientContract | None,
    buckets: RateLimitBucketAdapterContract,
    wall_clock: WallClock[Microseconds],
) -> SmsMessagingClientContract | None:
    """A business's SMS counted per hour, alerted and capped (LOG-05)."""

    if inner_client is None:
        return None

    return TenantSmsVolumeGuardAdapter(
        inner_client,
        buckets,
        BucketSignalCounterAdapter(buckets, wall_clock),
        wall_clock,
    )


def outbound_provider_slots(settings: AppSettings) -> ProviderSlotCount:
    """Half of this worker's outbound threads (WORKER_LANE_CONCURRENCY)."""

    return provider_slots_of_lane(
        settings.worker_lane_concurrency.get(JobLane.OUTBOUND, DEFAULT_OUTBOUND_THREADS)
    )
