from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.factories import build_otp_delivery_facilitator
from app.containers.notification_factories import build_staff_link_signer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.observability import JobMonitorFacilitatorContract
from app.facilitators.calendar.google_calendar_sync_facilitator import (
    GoogleCalendarSyncFacilitator,
)
from app.facilitators.channels.channel_message_sender_facilitator import (
    ChannelMessageSenderFacilitator,
)
from app.facilitators.events.event_publisher_facilitator import (
    EventPublisherFacilitator,
)
from app.facilitators.events.live_event_stream_facilitator import (
    LiveEventStreamFacilitator,
)
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.facilitators.notifications.manager_notification_facilitator import (
    ManagerNotificationFacilitator,
)
from app.facilitators.notifications.push_notification_queue_facilitator import (
    PushNotificationQueueFacilitator,
)
from app.facilitators.notifications.push_notification_sender_facilitator import (
    PushNotificationSenderFacilitator,
)
from app.facilitators.notifications.staff_alert_facilitator import (
    StaffAlertFacilitator,
)
from app.facilitators.notifications.staff_delivery_recorder_facilitator import (
    StaffDeliveryRecorderFacilitator,
)
from app.facilitators.notifications.staff_notification_sender_facilitator import (
    StaffNotificationSenderFacilitator,
)
from app.facilitators.observability.job_monitor_factory import (
    build_job_monitor_facilitator,
)
from app.facilitators.observability.sentry_error_reporting_facilitator import (
    SentryErrorReportingFacilitator,
)
from app.facilitators.product_events.record_product_event_facilitator import (
    RecordProductEventFacilitator,
)
from app.facilitators.setup.owner_nudge_facilitator import OwnerNudgeFacilitator
from app.facilitators.users.login_code_cap_alert_facilitator import (
    LoginCodeCapAlertFacilitator,
)
from app.facilitators.users.turnstile_bot_check_facilitator import (
    TurnstileBotCheckFacilitator,
)
from app.facilitators.value.owner_digest_facilitator import OwnerDigestFacilitator
from app.schemas.dto.live_events import LiveStreamLimits
from app.utilities.notifications.staff_link_signer import StaffLinkSigner


class FacilitatorsContainer(containers.DeclarativeContainer):
    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # Unexpected errors of the API and the worker, and errors of the website
    # widget (Sentry when SENTRY_DSN is set, otherwise the log), with the
    # release and a share of traced requests. The quality journal of model
    # calls is AdaptersContainer.llm_trace_facilitator.
    error_reporter: Singleton[SentryErrorReportingFacilitator] = Singleton(
        SentryErrorReportingFacilitator,
        dsn=config.app_settings.provided.sentry_dsn,
        environment=config.app_settings.provided.environment,
        release=config.app_settings.provided.release_version,
        traces_sample_rate=config.app_settings.provided.sentry_traces_sample_rate,
    )
    # Check-ins of the periodic jobs (Sentry Crons), with Sentry only.
    job_monitor: Singleton[JobMonitorFacilitatorContract] = Singleton(
        build_job_monitor_facilitator,
        error_reporter=error_reporter,
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
    # The cabinet's live updates: use cases publish what changed (ids only);
    # the SSE route opens streams, at most a few per person and process.
    event_publisher: Singleton[EventPublisherFacilitator] = Singleton(
        EventPublisherFacilitator,
        bus=adapters.live_event_bus,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The founder's product analytics: use cases report each step.
    product_events: Singleton[RecordProductEventFacilitator] = Singleton(
        RecordProductEventFacilitator,
        product_event_repo=repositories.product_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    live_stream_limits: Singleton[LiveStreamLimits] = Singleton(LiveStreamLimits)
    live_stream_facilitator: Singleton[LiveEventStreamFacilitator] = Singleton(
        LiveEventStreamFacilitator,
        bus=adapters.live_event_bus,
        limits=live_stream_limits,
    )
    # The durable job queue of the background workers.
    job_queue_facilitator: Singleton[JobQueueFacilitator] = Singleton(
        JobQueueFacilitator,
        job_repo=repositories.queued_job_repo,
        job_wakeup=adapters.job_wakeup,
        unit_of_work=adapters.storage_unit_of_work,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # Staff notifications are queued in the outbox; the worker sends them
    # through the platform Telegram bot, a WhatsApp template, e-mail (SMTP),
    # SMS (Twilio) or Web Push, and their delivery state is kept per
    # contact and device.
    staff_delivery_recorder: Singleton[StaffDeliveryRecorderFacilitator] = Singleton(
        StaffDeliveryRecorderFacilitator,
        staff_delivery_state_repo=repositories.staff_delivery_state_repo,
        push_subscription_repo=repositories.push_subscription_repo,
    )
    manager_notification_facilitator: Singleton[ManagerNotificationFacilitator] = (
        Singleton(
            ManagerNotificationFacilitator,
            outbound_message_repo=repositories.outbound_message_repo,
            job_queue=job_queue_facilitator,
            app_settings=config.app_settings,
            rate_limits=registries.request_rate_limit_registry,
            delivery_recorder=staff_delivery_recorder,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
    staff_notification_sender: Singleton[StaffNotificationSenderFacilitator] = (
        Singleton(
            StaffNotificationSenderFacilitator,
            telegram_client=clients.telegram_bot_client,
            whatsapp_templates=adapters.whatsapp_channel_adapter,
            app_settings=config.app_settings,
            email_client=clients.smtp_email_client,
            sms_client=clients.twilio_messaging_client,
        )
    )
    push_notification_queue: Singleton[PushNotificationQueueFacilitator] = Singleton(
        PushNotificationQueueFacilitator,
        outbound_message_repo=repositories.outbound_message_repo,
        job_queue=job_queue_facilitator,
        web_push_client=clients.web_push_client,
        rate_limits=registries.request_rate_limit_registry,
        delivery_recorder=staff_delivery_recorder,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    push_notification_sender: Singleton[PushNotificationSenderFacilitator] = Singleton(
        PushNotificationSenderFacilitator,
        push_subscription_repo=repositories.push_subscription_repo,
        web_push_client=clients.web_push_client,
    )
    # Signed, expiring links of notifications (key from ENCRYPTION_KEY).
    staff_link_signer: Singleton[StaffLinkSigner] = Singleton(
        build_staff_link_signer,
        settings=config.app_settings,
    )
    # Handoffs, requests and bookings to every contact and device of a
    # business, with preferences, quiet hours and links.
    staff_alert_facilitator: Singleton[StaffAlertFacilitator] = Singleton(
        StaffAlertFacilitator,
        manager_notifier=manager_notification_facilitator,
        push_queue=push_notification_queue,
        push_subscription_repo=repositories.push_subscription_repo,
        notification_preferences_repo=repositories.notification_preferences_repo,
        link_signer=staff_link_signer,
        text_transformer=transformers.staff_notification_text_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The owners' digests and monthly reports: e-mail and devices, once per
    # report and recipient, through the same outbox.
    owner_digest_facilitator: Singleton[OwnerDigestFacilitator] = Singleton(
        OwnerDigestFacilitator,
        user_repo=repositories.user_repo,
        digest_preferences_repo=repositories.digest_preferences_repo,
        push_subscription_repo=repositories.push_subscription_repo,
        notification_preferences_repo=repositories.notification_preferences_repo,
        manager_notifier=manager_notification_facilitator,
        push_queue=push_notification_queue,
        link_signer=staff_link_signer,
        text_transformer=transformers.value_digest_text_transformer,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # Activation nudges: e-mail, Telegram and devices, once per nudge and
    # recipient, through the same outbox.
    owner_nudge_facilitator: Singleton[OwnerNudgeFacilitator] = Singleton(
        OwnerNudgeFacilitator,
        user_repo=repositories.user_repo,
        push_subscription_repo=repositories.push_subscription_repo,
        notification_preferences_repo=repositories.notification_preferences_repo,
        manager_notifier=manager_notification_facilitator,
        push_queue=push_notification_queue,
        link_signer=staff_link_signer,
        localized_text_resolver=utilities.localized_text_resolver,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
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
        live_events=event_publisher,
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
