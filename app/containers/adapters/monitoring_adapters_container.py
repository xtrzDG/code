from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dependency, Singleton

from app.adapters.llm.metered_llm_adapter import MeteredLlmAdapter
from app.adapters.llm.signal_counting_llm_adapter import SignalCountingLlmAdapter
from app.adapters.monitoring.bucket_signal_counter_adapter import (
    BucketSignalCounterAdapter,
)
from app.adapters.monitoring.database_size_adapter_factory import (
    build_database_size_adapter,
)
from app.containers.clients import ClientsContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.monitoring import (
    DatabaseSizeAdapterContract,
    SignalCounterAdapterContract,
)


class MonitoringAdaptersContainer(containers.DeclarativeContainer):
    """
    The platform watching itself (docs/operations/slo.md): the shared
    signal counters of the alerts (in the rate-limit buckets), the language
    model decorated to count its calls and failures (`traced_llm_adapter`
    is the model it decorates) and measured for /metrics with a span per
    call, and the database's size for the admin system page.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # The RateLimitBucketAdapterContract and the LlmAdapterContract it
    # builds on (a Dependency checks no type).
    rate_limit_buckets: Dependency[object] = Dependency()
    traced_llm_adapter: Dependency[object] = Dependency()

    signal_counter: Singleton[SignalCounterAdapterContract] = Singleton(
        BucketSignalCounterAdapter,
        buckets=rate_limit_buckets,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    metered_llm_adapter: Singleton[MeteredLlmAdapter] = Singleton(
        MeteredLlmAdapter,
        inner_adapter=traced_llm_adapter,
        metrics=utilities.service_metrics,
        tracer=utilities.span_tracer,
        monotonic_clock=time_provider.monotonic_clock,
    )
    counted_llm_adapter: Singleton[SignalCountingLlmAdapter] = Singleton(
        SignalCountingLlmAdapter,
        inner_adapter=metered_llm_adapter,
        signal_counter=signal_counter,
    )
    database_size: Singleton[DatabaseSizeAdapterContract] = Singleton(
        build_database_size_adapter,
        connection_pool=clients.postgres_pool,
    )
