from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.notifications.notification_settings import (
    ContactCheckCommand,
    MyNotificationSettingsView,
    NotificationCheckQueued,
    NotificationContactList,
    NotificationContactsQuery,
    NotificationSettingsQuery,
    PushDeviceCommand,
    PushDeviceView,
    SubscribePushCommand,
    UpdateNotificationPreferencesCommand,
)
from app.schemas.dto.notifications.staff_links import StaffLinkQuery, StaffLinkView
from app.use_cases.notifications.get_notification_settings_use_case import (
    GetNotificationSettingsUseCase,
)
from app.use_cases.notifications.list_notification_contacts_use_case import (
    ListNotificationContactsUseCase,
)
from app.use_cases.notifications.queue_contact_check_use_case import (
    QueueContactCheckUseCase,
)
from app.use_cases.notifications.queue_device_check_use_case import (
    QueueDeviceCheckUseCase,
)
from app.use_cases.notifications.resolve_staff_link_use_case import (
    ResolveStaffLinkUseCase,
)
from app.use_cases.notifications.subscribe_push_use_case import SubscribePushUseCase
from app.use_cases.notifications.unsubscribe_push_use_case import (
    UnsubscribePushUseCase,
)
from app.use_cases.notifications.update_notification_preferences_use_case import (
    UpdateNotificationPreferencesUseCase,
)


class NotificationUseCasesContainer(containers.DeclarativeContainer):
    """
    Settings → Notifications: the staff contacts and their checks, each
    member's preferences and devices (Web Push), notification links.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    authorize = account_use_cases.authorize_business_access_use_case

    list_notification_contacts_use_case: Factory[
        UseCaseContract[NotificationContactsQuery, NotificationContactList]
    ] = Factory(
        ListNotificationContactsUseCase,
        authorize_business_access=authorize,
        staff_delivery_state_repo=repositories.staff_delivery_state_repo,
        app_settings=config.app_settings,
    )
    queue_contact_check_use_case: Factory[
        UseCaseContract[ContactCheckCommand, NotificationCheckQueued]
    ] = Factory(
        QueueContactCheckUseCase,
        authorize_business_access=authorize,
        outbound_message_repo=repositories.outbound_message_repo,
        delivery_recorder=facilitators.staff_delivery_recorder,
        rate_limits=registries.request_rate_limit_registry,
        brief_transformer=transformers.staff_alert_brief_transformer,
        text_transformer=transformers.staff_notification_text_transformer,
        link_signer=facilitators.staff_link_signer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_notification_settings_use_case: Factory[
        UseCaseContract[NotificationSettingsQuery, MyNotificationSettingsView]
    ] = Factory(
        GetNotificationSettingsUseCase,
        authorize_business_access=authorize,
        notification_preferences_repo=repositories.notification_preferences_repo,
        push_subscription_repo=repositories.push_subscription_repo,
        web_push_client=clients.web_push_client,
    )
    update_notification_preferences_use_case: Factory[
        UseCaseContract[
            UpdateNotificationPreferencesCommand, MyNotificationSettingsView
        ]
    ] = Factory(
        UpdateNotificationPreferencesUseCase,
        authorize_business_access=authorize,
        notification_preferences_repo=repositories.notification_preferences_repo,
        push_subscription_repo=repositories.push_subscription_repo,
        web_push_client=clients.web_push_client,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    subscribe_push_use_case: Factory[
        UseCaseContract[SubscribePushCommand, PushDeviceView]
    ] = Factory(
        SubscribePushUseCase,
        authorize_business_access=authorize,
        push_subscription_repo=repositories.push_subscription_repo,
        web_push_client=clients.web_push_client,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    unsubscribe_push_use_case: Factory[UseCaseContract[PushDeviceCommand, None]] = (
        Factory(
            UnsubscribePushUseCase,
            authorize_business_access=authorize,
            push_subscription_repo=repositories.push_subscription_repo,
        )
    )
    queue_device_check_use_case: Factory[
        UseCaseContract[PushDeviceCommand, NotificationCheckQueued]
    ] = Factory(
        QueueDeviceCheckUseCase,
        authorize_business_access=authorize,
        push_subscription_repo=repositories.push_subscription_repo,
        outbound_message_repo=repositories.outbound_message_repo,
        rate_limits=registries.request_rate_limit_registry,
        brief_transformer=transformers.staff_alert_brief_transformer,
        link_signer=facilitators.staff_link_signer,
        web_push_client=clients.web_push_client,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resolve_staff_link_use_case: Factory[
        UseCaseContract[StaffLinkQuery, StaffLinkView]
    ] = Factory(
        ResolveStaffLinkUseCase,
        authorize_business_access=authorize,
        link_signer=facilitators.staff_link_signer,
        booking_repo=repositories.booking_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
