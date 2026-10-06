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
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.growth.campaign_views import (
    CampaignMessagePage,
    CampaignMessagePageQuery,
    CampaignSettingsQuery,
    CampaignSettingsView,
    UpdateCampaignSettingsCommand,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.use_cases.campaigns.campaign_settings_views import CampaignSettingsReader
from app.use_cases.campaigns.campaign_writer import CampaignWriter
from app.use_cases.campaigns.get_campaign_settings_use_case import (
    GetCampaignSettingsUseCase,
)
from app.use_cases.campaigns.list_campaign_messages_use_case import (
    ListCampaignMessagesUseCase,
)
from app.use_cases.campaigns.run_rebooking_campaigns_use_case import (
    RunRebookingCampaignsUseCase,
)
from app.use_cases.campaigns.update_campaign_settings_use_case import (
    UpdateCampaignSettingsUseCase,
)
from app.use_cases.shared.customer_segment_members import SegmentReaders
from app.use_cases.shared.proactive_letters import ProactiveSender
from app.use_cases.shared.proactive_routes import ProactiveRouting


class CampaignUseCasesContainer(containers.DeclarativeContainer):
    """
    The rebooking campaigns (1151): the hourly job that writes to the
    customers each business's rule finds, and Bookings → Return visits
    (the owner's opt-in, rule, audience and cap; the messages written).
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    authorize = account_use_cases.authorize_business_access_use_case
    wall_clock = time_provider.microsecond_wall_clock

    settings_reader: Factory[CampaignSettingsReader] = Factory(
        CampaignSettingsReader,
        message_repo=repositories.campaign_message_repo,
        segment_repo=repositories.customer_segment_repo,
        rule_registry=registries.rebooking_rule_registry,
        text_resolver=utilities.localized_text_resolver,
    )
    run_rebooking_campaigns_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            RunRebookingCampaignsUseCase,
            campaign_settings_repo=repositories.campaign_settings_repo,
            campaign_message_repo=repositories.campaign_message_repo,
            business_repo=repositories.business_repo,
            booking_repo=repositories.booking_repo,
            contact_repo=repositories.contact_repo,
            customer_segment_repo=repositories.customer_segment_repo,
            segment_readers=Factory(
                SegmentReaders,
                card_repo=repositories.contact_repo,
                activity_repo=repositories.contact_activity_repo,
                history_repo=repositories.customer_history_repo,
            ),
            writer=Factory(
                CampaignWriter,
                message_repo=repositories.campaign_message_repo,
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
                text_resolver=utilities.localized_text_resolver,
                live_events=facilitators.event_publisher,
                suppression_list=facilitators.suppression_list,
                whatsapp_template=(
                    config.app_settings.provided.growth.rebooking_template_name
                ),
            ),
            wall_clock=wall_clock,
        )
    )
    get_campaign_settings_use_case: Factory[
        UseCaseContract[CampaignSettingsQuery, CampaignSettingsView]
    ] = Factory(
        GetCampaignSettingsUseCase,
        authorize_business_access=authorize,
        campaign_settings_repo=repositories.campaign_settings_repo,
        reader=settings_reader,
        wall_clock=wall_clock,
    )
    update_campaign_settings_use_case: Factory[
        UseCaseContract[UpdateCampaignSettingsCommand, CampaignSettingsView]
    ] = Factory(
        UpdateCampaignSettingsUseCase,
        authorize_business_access=authorize,
        campaign_settings_repo=repositories.campaign_settings_repo,
        customer_segment_repo=repositories.customer_segment_repo,
        audit_log_repo=repositories.audit_log_repo,
        reader=settings_reader,
        wall_clock=wall_clock,
    )
    list_campaign_messages_use_case: Factory[
        UseCaseContract[CampaignMessagePageQuery, CampaignMessagePage]
    ] = Factory(
        ListCampaignMessagesUseCase,
        authorize_business_access=authorize,
        campaign_message_repo=repositories.campaign_message_repo,
        contact_repo=repositories.contact_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=wall_clock,
    )
