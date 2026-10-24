"""
The website widget's use cases (the chat's configuration, the poll of a
visitor's answers, the live stream's ticket, a visitor's message and the
cabinet's snippet), built over the channel context's edges:
`ChannelUseCasesContainer` holds them as its own providers.
"""

from dataclasses import dataclass

from dependency_injector.providers import Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.channels.widget import (
    WidgetConfigView,
    WidgetMessageCommand,
    WidgetMessagesQuery,
    WidgetMessagesView,
    WidgetSnippetQuery,
    WidgetSnippetView,
)
from app.schemas.dto.channels.widget_streams import WidgetStreamTicketRequest
from app.schemas.dto.channels.widget_uploads import AcceptedWidgetMessage
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.use_cases.channels.accept_widget_message_use_case import (
    AcceptWidgetMessageUseCase,
)
from app.use_cases.channels.get_widget_config_use_case import GetWidgetConfigUseCase
from app.use_cases.channels.get_widget_messages_use_case import GetWidgetMessagesUseCase
from app.use_cases.channels.get_widget_snippet_use_case import GetWidgetSnippetUseCase
from app.use_cases.channels.widget_stream.issue_widget_stream_ticket_use_case import (
    IssueWidgetStreamTicketUseCase,
)


@dataclass(frozen=True)
class WidgetUseCaseProviders:
    """The widget's use case providers, typed by their contracts."""

    get_widget_config_use_case: Factory[UseCaseContract[BusinessId, WidgetConfigView]]
    # Singleton: it remembers the web chats it found open (OpenChatMemory).
    get_widget_messages_use_case: Singleton[
        UseCaseContract[WidgetMessagesQuery, WidgetMessagesView]
    ]
    # A ticket to the visitor's live stream with each widget answer.
    issue_widget_stream_ticket_use_case: Factory[
        UseCaseContract[WidgetStreamTicketRequest, WidgetStreamTicket]
    ]
    accept_widget_message_use_case: Factory[
        UseCaseContract[WidgetMessageCommand, AcceptedWidgetMessage]
    ]
    get_widget_snippet_use_case: Factory[
        UseCaseContract[WidgetSnippetQuery, WidgetSnippetView]
    ]


def build_widget_use_case_providers(
    account_use_cases: AccountUseCasesContainer,
    adapters: AdaptersContainer,
    config: ConfigContainer,
    facilitators: FacilitatorsContainer,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    utilities: UtilitiesContainer,
) -> WidgetUseCaseProviders:
    """The widget's providers over the channel context's edges."""

    return WidgetUseCaseProviders(
        get_widget_config_use_case=Factory(
            GetWidgetConfigUseCase,
            business_repo=repositories.business_repo,
            channel_repo=repositories.channel_repo,
            assistant_version_repo=repositories.assistant_version_repo,
            business_profile_repo=repositories.business_profile_repo,
            knowledge_item_repo=repositories.knowledge_item_repo,
            language_registry=registries.language_registry,
            language_detector=utilities.language_detector,
            app_settings=config.app_settings,
            referral_links=facilitators.referral_links,
            starter_answer_registry=registries.starter_answer_registry,
        ),
        get_widget_messages_use_case=Singleton(
            GetWidgetMessagesUseCase,
            channel_repo=repositories.channel_repo,
            conversation_repo=repositories.conversation_repo,
            message_repo=repositories.message_repo,
            business_limits_repo=repositories.business_limits_repo,
            language_registry=registries.language_registry,
            rate_limit_registry=registries.request_rate_limit_registry,
            wall_clock=time_provider.microsecond_wall_clock,
            platform_origins=utilities.widget_platform_origins,
            read_session=adapters.storage_read_session,
            poll_reads=adapters.widget_poll_reads,
        ),
        issue_widget_stream_ticket_use_case=Factory(
            IssueWidgetStreamTicketUseCase,
            ticket_signer=utilities.widget_stream_ticket_signer,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
        accept_widget_message_use_case=Factory(
            AcceptWidgetMessageUseCase,
            business_repo=repositories.business_repo,
            channel_repo=repositories.channel_repo,
            rate_limit_registry=registries.request_rate_limit_registry,
            wall_clock=time_provider.microsecond_wall_clock,
            widget_upload_repo=repositories.widget_upload_repo,
        ),
        get_widget_snippet_use_case=Factory(
            GetWidgetSnippetUseCase,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            app_settings=config.app_settings,
        ),
    )
