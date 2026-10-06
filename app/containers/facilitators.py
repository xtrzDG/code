from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.invoicing_facilitators import InvoicingFacilitatorsContainer
from app.containers.notification_factories import build_staff_link_signer
from app.containers.privacy_facilitators import PrivacyFacilitatorsContainer
from app.containers.referral_facilitators import ReferralFacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.sign_in_facilitators import SignInFacilitatorsContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.observability import JobMonitorFacilitatorContract
from app.facilitators.calendar.google_calendar_sync_facilitator import (
    GoogleCalendarSyncFacilitator,
)
from app.facilitators.channels.typing_signal_facilitator import (
    TypingSignalFacilitator,
)
from app.facilitators.claim_check.claim_check_facilitator import (
    ClaimCheckFacilitator,
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
from app.facilitators.privacy.export_download_notice_facilitator import (
    ExportDownloadNoticeFacilitator,
)
from app.facilitators.product_events.record_product_event_facilitator import (
    RecordProductEventFacilitator,
)
from app.facilitators.setup.owner_nudge_facilitator import OwnerNudgeFacilitator
from app.facilitators.users.sign_in_notice_facilitator import SignInNoticeFacilitator
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

    # Errors of the API, the worker and the widget (Sentry, else the log); the
    # quality journal of model calls is AdaptersContainer.llm_trace_facilitator.
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
    # Sign-in codes and the login's abuse protection.
    sign_in: SignInFacilitatorsContainer = Container(  # type: ignore[assignment]
        SignInFacilitatorsContainer, adapters=adapters, clients=clients,
        config=config, time_provider=time_provider, utilities=utilities,
    )  # fmt: skip
    otp_delivery_facilitator = sign_in.otp_delivery_facilitator
    bot_check_facilitator = sign_in.bot_check_facilitator
    login_code_cap_alerts = sign_in.login_code_cap_alerts
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
    # Staff notifications go through the outbox (Telegram bot, WhatsApp, e-mail,
    # SMS, Web Push); their delivery state is kept per contact and device.
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
    # A sign-in from a new device: the person's devices and e-mail (1103).
    sign_in_notice_facilitator: Singleton[SignInNoticeFacilitator] = Singleton(
        SignInNoticeFacilitator,
        business_repo=repositories.business_repo,
        staff_alerts=staff_alert_facilitator,
        manager_notifier=manager_notification_facilitator,
        text_transformer=transformers.staff_notification_text_transformer,
        link_signer=staff_link_signer,
        localized_text_resolver=utilities.localized_text_resolver,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # A download of a full export: every owner's devices and e-mail or SMS.
    export_download_notice_facilitator: Singleton[ExportDownloadNoticeFacilitator] = (
        Singleton(
            ExportDownloadNoticeFacilitator,
            user_repo=repositories.user_repo,
            staff_alerts=staff_alert_facilitator,
            manager_notifier=manager_notification_facilitator,
            text_transformer=transformers.staff_notification_text_transformer,
            link_signer=staff_link_signer,
            localized_text_resolver=utilities.localized_text_resolver,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        )
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
    # Data-subject rights: the suppression list, the sub-processors' copies.
    privacy: PrivacyFacilitatorsContainer = Container(  # type: ignore[assignment]
        PrivacyFacilitatorsContainer, clients=clients, config=config,
        repositories=repositories, job_queue=job_queue_facilitator,
    )  # fmt: skip
    suppression_list = privacy.suppression_list
    processor_erasure = privacy.processor_erasure
    # The claim check of the reply guard: a cheap verifier model
    # (LLM_VERIFIER_MODEL_ID; none: the check is off).
    claim_check: Singleton[ClaimCheckFacilitator] = Singleton(
        ClaimCheckFacilitator,
        llm_adapter=adapters.chat_llm_adapter,
        verifier_model_id=config.app_settings.provided.reply_safety.llm_verifier_model_id,
    )
    # "typing…" while a reply is written (Telegram, WhatsApp, Meta pages).
    typing_signals: Singleton[TypingSignalFacilitator] = Singleton(
        TypingSignalFacilitator,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        telegram_adapter=adapters.telegram_channel_adapter,
        whatsapp_adapter=adapters.whatsapp_channel_adapter,
        messenger_adapter=adapters.messenger_channel_adapter,
        instagram_adapter=adapters.instagram_channel_adapter,
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
    # Invoice numbers, VAT and the invoice and receipt PDFs (1114).
    invoicing: InvoicingFacilitatorsContainer = Container(  # type: ignore[assignment]
        InvoicingFacilitatorsContainer, adapters=adapters, config=config,
        registries=registries, repositories=repositories,
        time_provider=time_provider, transformers=transformers,
    )  # fmt: skip
    invoice_issuing_facilitator = invoicing.invoice_issuing_facilitator
    billing_document_facilitator = invoicing.billing_document_facilitator
    billing_email_attachments = invoicing.billing_email_attachments_facilitator
    # The referral program (1150): "Powered by" and invitation links, who
    # brought a business, what its paid invoices earn.
    referrals: ReferralFacilitatorsContainer = Container(  # type: ignore[assignment]
        ReferralFacilitatorsContainer, config=config, registries=registries,
        repositories=repositories, time_provider=time_provider,
        utilities=utilities,
    )  # fmt: skip
    referral_links = referrals.referral_links
    referral_attribution = referrals.referral_attribution
    referral_earnings = referrals.referral_earnings
