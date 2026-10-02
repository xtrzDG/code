from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.factories import build_otp_delivery_facilitator
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.facilitators.calendar.google_calendar_sync_facilitator import (
    GoogleCalendarSyncFacilitator,
)
from app.facilitators.channels.channel_message_sender_facilitator import (
    ChannelMessageSenderFacilitator,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.facilitators.notifications.manager_notification_facilitator import (
    ManagerNotificationFacilitator,
)
from app.facilitators.notifications.staff_notification_sender_facilitator import (
    StaffNotificationSenderFacilitator,
)
from app.facilitators.observability.sentry_error_reporting_facilitator import (
    SentryErrorReportingFacilitator,
)
from app.facilitators.staff.manager_broadcast_facilitator import (
    ManagerBroadcastFacilitator,
)
from app.facilitators.users.login_code_cap_alert_facilitator import (
    LoginCodeCapAlertFacilitator,
)
from app.facilitators.users.turnstile_bot_check_facilitator import (
    TurnstileBotCheckFacilitator,
)


class FacilitatorsContainer(containers.DeclarativeContainer):
    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # Unexpected errors of the API and the worker (Sentry when SENTRY_DSN is
    # set, otherwise the log). The quality journal of model calls is
    # AdaptersContainer.llm_trace_facilitator.
    error_reporter: Singleton[SentryErrorReportingFacilitator] = Singleton(
        SentryErrorReportingFacilitator,
        dsn=config.app_settings.provided.sentry_dsn,
        environment=config.app_settings.provided.environment,
    )
    # Sign-in codes: Twilio SMS, Telegram Gateway, WhatsApp authentication
    # template and SMTP e-mail, each when configured; in development and test
    # the other channels write the code to the log.
    otp_delivery_facilitator: Singleton[OtpDeliveryFacilitatorContract] = Singleton(
        build_otp_delivery_facilitator,
        settings=config.app_settings,
        sms_client=clients.twilio_messaging_client,
        telegram_gateway_client=clients.telegram_gateway_client,
        whatsapp_client=clients.whatsapp_authentication_client,
        email_client=clients.smtp_email_client,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    # Login abuse protection: the Turnstile check of risky code requests
    # (off without TURNSTILE_* keys) and the alert when a cap refuses sends.
    bot_check_facilitator: Singleton[TurnstileBotCheckFacilitator] = Singleton(
        TurnstileBotCheckFacilitator,
        verification_client=clients.turnstile_verification_client,
        site_key=config.app_settings.provided.turnstile_site_key,
    )
    login_code_cap_alerts: Singleton[LoginCodeCapAlertFacilitator] = Singleton(
        LoginCodeCapAlertFacilitator,
        email_client=clients.smtp_email_client,
        platform_admin_emails=config.app_settings.provided.platform_admin_emails,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The durable job queue of the background workers.
    job_queue_facilitator: Singleton[JobQueueFacilitator] = Singleton(
        JobQueueFacilitator,
        job_repo=repositories.queued_job_repo,
        job_wakeup=utilities.job_wakeup,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # Staff notifications are queued in the outbox; the worker sends them
    # through the platform Telegram bot, a WhatsApp template or e-mail.
    manager_notification_facilitator: Singleton[ManagerNotificationFacilitator] = (
        Singleton(
            ManagerNotificationFacilitator,
            outbound_message_repo=repositories.outbound_message_repo,
            job_queue=job_queue_facilitator,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    staff_notification_sender: Singleton[StaffNotificationSenderFacilitator] = (
        Singleton(
            StaffNotificationSenderFacilitator,
            telegram_client=clients.telegram_bot_client,
            whatsapp_templates=adapters.whatsapp_channel_adapter,
            app_settings=config.app_settings,
        )
    )
    manager_broadcast_facilitator: Singleton[ManagerBroadcastFacilitator] = Singleton(
        ManagerBroadcastFacilitator,
        notifier=manager_notification_facilitator,
    )
    # Proactive messages to customers through the business's own messengers.
    channel_message_sender: Singleton[ChannelMessageSenderFacilitator] = Singleton(
        ChannelMessageSenderFacilitator,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        telegram_adapter=adapters.telegram_channel_adapter,
        whatsapp_adapter=adapters.whatsapp_channel_adapter,
        messenger_adapter=adapters.messenger_channel_adapter,
        instagram_adapter=adapters.instagram_channel_adapter,
        whatsapp_templates=adapters.whatsapp_channel_adapter,
        usage_event_repo=repositories.usage_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    calendar_sync_facilitator: Singleton[GoogleCalendarSyncFacilitator] = Singleton(
        GoogleCalendarSyncFacilitator,
        connection_repo=repositories.calendar_connection_repo,
        event_link_repo=repositories.calendar_event_link_repo,
        business_repo=repositories.business_repo,
        resource_repo=repositories.resource_repo,
        contact_repo=repositories.contact_repo,
        calendar_client=clients.google_calendar_client,
        secret_cipher=adapters.secret_cipher,
        phone_number_parser=utilities.phone_number_parser,
        event_text_transformer=transformers.calendar_event_text_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
