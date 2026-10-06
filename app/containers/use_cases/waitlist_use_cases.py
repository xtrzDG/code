from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.booking_use_cases import BookingUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.conversation_engine import PreparedTurn
from app.schemas.dto.feedback.customer_signals import CustomerSignalReply
from app.schemas.dto.growth.waitlist_joining import (
    JoinWaitlistCommand,
    WaitlistJoinReceipt,
)
from app.schemas.dto.growth.waitlist_views import (
    RemoveWaitlistEntryCommand,
    UpdateWaitlistSettingsCommand,
    WaitlistEntryPage,
    WaitlistPageQuery,
    WaitlistSettingsQuery,
    WaitlistSettingsView,
)
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.use_cases.shared.proactive_letters import ProactiveSender
from app.use_cases.shared.proactive_routes import ProactiveRouting
from app.use_cases.waitlist.answer_waitlist_offer_use_case import (
    AnswerWaitlistOfferUseCase,
)
from app.use_cases.waitlist.expire_waitlist_offers_use_case import (
    ExpireWaitlistOffersUseCase,
)
from app.use_cases.waitlist.get_waitlist_settings_use_case import (
    GetWaitlistSettingsUseCase,
)
from app.use_cases.waitlist.join_waitlist_use_case import JoinWaitlistUseCase
from app.use_cases.waitlist.list_waitlist_use_case import ListWaitlistUseCase
from app.use_cases.waitlist.offer_delivery import WaitlistOfferDelivery
from app.use_cases.waitlist.offer_freed_place_use_case import OfferFreedPlaceUseCase
from app.use_cases.waitlist.remove_waitlist_entry_use_case import (
    RemoveWaitlistEntryUseCase,
)
from app.use_cases.waitlist.update_waitlist_settings_use_case import (
    UpdateWaitlistSettingsUseCase,
)


class WaitlistUseCasesContainer(containers.DeclarativeContainer):
    """
    The waitlist (1151): the assistant's join_waitlist tool, the offer of a
    freed place (queued job), the customer's yes or no (before the
    assistant), the hold's expiry (periodic job), Bookings → Waitlist.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    booking_use_cases: BookingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    authorize = account_use_cases.authorize_business_access_use_case
    wall_clock = time_provider.microsecond_wall_clock

    join_waitlist_use_case: Factory[
        UseCaseContract[JoinWaitlistCommand, WaitlistJoinReceipt]
    ] = Factory(
        JoinWaitlistUseCase,
        business_repo=repositories.business_repo,
        waitlist_settings_repo=repositories.waitlist_settings_repo,
        waitlist_entry_repo=repositories.waitlist_entry_repo,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        contact_repo=repositories.contact_repo,
        check_availability=booking_use_cases.check_availability_use_case,
        live_events=facilitators.event_publisher,
        wall_clock=wall_clock,
    )
    offer_delivery: Factory[WaitlistOfferDelivery] = Factory(
        WaitlistOfferDelivery,
        routing=Factory(
            ProactiveRouting,
            channel_repo=repositories.channel_repo,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
        ),
        sender=Factory(
            ProactiveSender,
            outbound_message_repo=repositories.outbound_message_repo,
            job_queue=facilitators.job_queue_facilitator,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
            unit_of_work=adapters.storage_unit_of_work,
        ),
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        text_resolver=utilities.localized_text_resolver,
        live_events=facilitators.event_publisher,
        whatsapp_template=config.app_settings.provided.growth.waitlist_template_name,
    )
    offer_freed_place_use_case: Factory[UseCaseContract[QueuedJobInput, JobReport]] = (
        Factory(
            OfferFreedPlaceUseCase,
            business_repo=repositories.business_repo,
            business_profile_repo=repositories.business_profile_repo,
            waitlist_settings_repo=repositories.waitlist_settings_repo,
            waitlist_entry_repo=repositories.waitlist_entry_repo,
            booking_repo=repositories.booking_repo,
            resource_repo=repositories.resource_repo,
            lock_registry=registries.business_lock_registry,
            delivery=offer_delivery,
            live_events=facilitators.event_publisher,
            wall_clock=wall_clock,
        )
    )
    answer_waitlist_offer_use_case: Factory[
        UseCaseContract[PreparedTurn, CustomerSignalReply | None]
    ] = Factory(
        AnswerWaitlistOfferUseCase,
        waitlist_entry_repo=repositories.waitlist_entry_repo,
        message_repo=repositories.message_repo,
        resource_repo=repositories.resource_repo,
        create_booking=booking_use_cases.create_booking_use_case,
        send_confirmation=booking_use_cases.send_booking_confirmation_use_case,
        job_queue=facilitators.job_queue_facilitator,
        text_resolver=utilities.localized_text_resolver,
        live_events=facilitators.event_publisher,
        wall_clock=wall_clock,
    )
    expire_waitlist_offers_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            ExpireWaitlistOffersUseCase,
            waitlist_entry_repo=repositories.waitlist_entry_repo,
            lock_registry=registries.business_lock_registry,
            job_queue=facilitators.job_queue_facilitator,
            live_events=facilitators.event_publisher,
            wall_clock=wall_clock,
        )
    )
    list_waitlist_use_case: Factory[
        UseCaseContract[WaitlistPageQuery, WaitlistEntryPage]
    ] = Factory(
        ListWaitlistUseCase,
        authorize_business_access=authorize,
        waitlist_entry_repo=repositories.waitlist_entry_repo,
        contact_repo=repositories.contact_repo,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
    remove_waitlist_entry_use_case: Factory[
        UseCaseContract[RemoveWaitlistEntryCommand, None]
    ] = Factory(
        RemoveWaitlistEntryUseCase,
        authorize_business_access=authorize,
        waitlist_entry_repo=repositories.waitlist_entry_repo,
        audit_log_repo=repositories.audit_log_repo,
        job_queue=facilitators.job_queue_facilitator,
        live_events=facilitators.event_publisher,
        wall_clock=wall_clock,
    )
    get_waitlist_settings_use_case: Factory[
        UseCaseContract[WaitlistSettingsQuery, WaitlistSettingsView]
    ] = Factory(
        GetWaitlistSettingsUseCase,
        authorize_business_access=authorize,
        waitlist_settings_repo=repositories.waitlist_settings_repo,
        waitlist_entry_repo=repositories.waitlist_entry_repo,
    )
    update_waitlist_settings_use_case: Factory[
        UseCaseContract[UpdateWaitlistSettingsCommand, WaitlistSettingsView]
    ] = Factory(
        UpdateWaitlistSettingsUseCase,
        authorize_business_access=authorize,
        waitlist_settings_repo=repositories.waitlist_settings_repo,
        waitlist_entry_repo=repositories.waitlist_entry_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
