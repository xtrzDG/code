from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.integration_facilitators import IntegrationFacilitatorsContainer
from app.containers.time_provider import TimeProviderContainer
from app.facilitators.events.event_publisher_facilitator import (
    EventPublisherFacilitator,
)
from app.facilitators.events.live_event_stream_facilitator import (
    LiveEventStreamFacilitator,
)
from app.facilitators.events.widget_event_stream_facilitator import (
    WidgetEventStreamFacilitator,
)
from app.schemas.dto.channels.widget_streams import WidgetStreamLimits
from app.schemas.dto.live_events import LiveStreamLimits


class LiveFacilitatorsContainer(containers.DeclarativeContainer):
    """
    Live updates over the live event bus: use cases publish what changed
    (ids only); the cabinet's SSE route opens streams, at most a few per
    person and process; the website chat's SSE route opens one per open
    widget, which hears only its own visitor's typing and answers. A child
    of FacilitatorsContainer, which names its providers flat
    (`facilitators.event_publisher`).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    integrations: IntegrationFacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # Webhooks hear every announced change first (`EmitBusinessEventFacilitator`).
    event_publisher: Singleton[EventPublisherFacilitator] = Singleton(
        EventPublisherFacilitator,
        bus=adapters.live_event_bus,
        wall_clock=time_provider.microsecond_wall_clock,
        observers=integrations.business_event_observers,
    )
    live_stream_limits: Singleton[LiveStreamLimits] = Singleton(LiveStreamLimits)
    live_stream_facilitator: Singleton[LiveEventStreamFacilitator] = Singleton(
        LiveEventStreamFacilitator,
        bus=adapters.live_event_bus,
        limits=live_stream_limits,
    )
    widget_stream_limits: Singleton[WidgetStreamLimits] = Singleton(WidgetStreamLimits)
    widget_stream_facilitator: Singleton[WidgetEventStreamFacilitator] = Singleton(
        WidgetEventStreamFacilitator,
        bus=adapters.live_event_bus,
        limits=widget_stream_limits,
    )
