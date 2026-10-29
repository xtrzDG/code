from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.inbound_bursts import HeldInboundEvents, InboundBurst
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.channels.inbox.claim_inbound_burst_use_case import (
    ClaimInboundBurstUseCase,
)
from app.use_cases.channels.inbox.finish_held_inbound_events_use_case import (
    FinishHeldInboundEventsUseCase,
)
from app.use_cases.channels.inbox.send_holding_reply_use_case import (
    SendHoldingReplyUseCase,
)


class ReplySpeedUseCasesContainer(containers.DeclarativeContainer):
    """
    How fast a customer hears back: quick messages in a row answered in one
    turn (MESSAGE_COALESCE_SECONDS) and the "one moment" of a turn past
    CHAT_TURN_DEADLINE_SECONDS.
    """

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    claim_inbound_burst_use_case: Factory[
        UseCaseContract[QueuedJobInput, InboundBurst | None]
    ] = Factory(
        ClaimInboundBurstUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
        coalesce_seconds=config.app_settings.provided.reply_speed.message_coalesce_seconds,
    )
    finish_held_inbound_events_use_case: Factory[
        UseCaseContract[HeldInboundEvents, ProcessedItemCount]
    ] = Factory(
        FinishHeldInboundEventsUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_holding_reply_use_case: Factory[
        UseCaseContract[InboundEventDocument, MessageId | None]
    ] = Factory(
        SendHoldingReplyUseCase,
        business_repo=repositories.business_repo,
        message_repo=repositories.message_repo,
        conversation_repo=repositories.conversation_repo,
        outbound_message_repo=repositories.outbound_message_repo,
        job_queue=facilitators.job_queue_facilitator,
        localized_text_resolver=utilities.localized_text_resolver,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
        reply_locks=registries.reply_lock_registry,
    )
