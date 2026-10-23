from dependency_injector.providers import Factory, Singleton

from app.adapters.documents.weasyprint_deletion_certificate_renderer_adapter import (
    WeasyPrintDeletionCertificateRendererAdapter,
)
from app.adapters.media.media_storage_factory import build_media_storage
from app.clients.meta.meta_subscription_client import MetaSubscriptionClient
from app.containers.account_deletion.account_deletion_dependencies import (
    AccountDeletionDependencies,
)
from app.containers.account_deletion.account_deletion_root import AccountDeletionRoot
from app.containers.account_deletion_factories import (
    build_business_row_eraser,
    build_deletion_ledger_mirror,
)
from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.assistant_use_cases import AssistantUseCasesContainer
from app.containers.use_cases.scheduling_use_cases import (
    SchedulingUseCasesContainer,
)
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.containers.utilities import UtilitiesContainer


def account_deletion_root_provider(
    *,
    adapters: AdaptersContainer,
    clients: ClientsContainer,
    config: ConfigContainer,
    facilitators: FacilitatorsContainer,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    utilities: UtilitiesContainer,
    account_use_cases: AccountUseCasesContainer,
    assistant_use_cases: AssistantUseCasesContainer,
    scheduling_use_cases: SchedulingUseCasesContainer,
    voice_use_cases: VoiceUseCasesContainer,
) -> Singleton[AccountDeletionRoot]:
    """
    The account deletion context's one root (R15, migration 1220), its
    dependencies taken from the graph: the single seam between the
    providers and the typed root (app/containers/account_deletion/, ADR
    0010; a missing or misspelt field fails
    test_every_provider_of_the_container_resolves).
    """

    return Singleton(
        AccountDeletionRoot,
        dependencies=Factory(
            AccountDeletionDependencies,
            authorize_business_access=account_use_cases.authorize_business_access_use_case,
            step_up=utilities.step_up_guard,
            storage_scope=utilities.storage_scope,
            closure_repo=repositories.business_closure_repo,
            deletion_repo=repositories.business_deletion_repo,
            business_repo=repositories.business_repo,
            channel_repo=repositories.channel_repo,
            brand_repo=repositories.brand_repo,
            user_repo=repositories.user_repo,
            audit_log_repo=repositories.audit_log_repo,
            subscription_repo=repositories.subscription_repo,
            invoice_repo=repositories.invoice_repo,
            payment_gateway=adapters.payment_gateway,
            payment_order_repo=repositories.payment_order_repo,
            remove_voice_agent=voice_use_cases.remove_voice_agent_use_case,
            resume_assistant=assistant_use_cases.resume_assistant_use_case,
            manager_notifier=facilitators.manager_notification_facilitator,
            localized_text_resolver=utilities.localized_text_resolver,
            job_queue=facilitators.job_queue_facilitator,
            job_repo=repositories.queued_job_repo,
            assistant_version_repo=repositories.assistant_version_repo,
            disconnect_google_calendar=scheduling_use_cases.disconnect_google_calendar_use_case,
            phone_number_repo=repositories.phone_number_repo,
            phone_number_provisioner=adapters.phone_number_provisioner,
            phone_line_lock=registries.phone_line_lock_registry,
            secret_cipher=adapters.secret_cipher,
            telegram_client=clients.telegram_bot_client,
            meta_subscriptions=Singleton(MetaSubscriptionClient),
            conversation_pages=repositories.conversation_repo,
            call_pages=repositories.call_repo,
            message_media_pages=repositories.message_media_repo,
            widget_upload_pages=repositories.widget_upload_repo,
            business_export_pages=repositories.business_export_repo,
            llm_turn_repo=repositories.llm_turn_repo,
            recording_storage=adapters.recording_storage,
            # The customers' files' storage, built as the media adapters build
            # it (a stateless adapter over the same bucket or folder).
            media_storage=Singleton(
                build_media_storage,
                settings=config.app_settings,
                object_storage_client=clients.object_storage_client,
            ),
            export_archive_storage=adapters.export_archive_storage,
            processor_erasure=facilitators.processor_erasure,
            row_eraser=Singleton(
                build_business_row_eraser,
                connection_pools=clients.postgres_pools,
                registry=clients.in_memory_collections,
            ),
            ledger_mirror=Singleton(
                build_deletion_ledger_mirror, settings=config.app_settings
            ),
            certificate_renderer=Singleton(
                WeasyPrintDeletionCertificateRendererAdapter
            ),
            user_session_repo=repositories.user_session_repo,
            totp_factor_repo=repositories.totp_factor_repo,
            recovery_code_repo=repositories.recovery_code_repo,
            passkey_repo=repositories.passkey_repo,
            push_subscription_repo=repositories.push_subscription_repo,
            notification_preferences_repo=repositories.notification_preferences_repo,
            security_nudge_repo=repositories.security_nudge_repo,
            platform_admins=registries.platform_admin_registry,
            app_settings=config.app_settings,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )
