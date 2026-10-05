from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Dict, Factory, List

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.operators.operators_container import OperatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.gateways.worker.background_worker import BackgroundWorker, PeriodicJobSpec
from app.gateways.worker.heartbeat_recorder import WorkerHeartbeatRecorder
from app.gateways.worker.periodic.activation_follow_up import (
    notice_milestones_job,
    send_activation_nudges_job,
)
from app.gateways.worker.periodic.channel_credentials import (
    check_channel_credentials_job,
)
from app.gateways.worker.periodic.end_expired_support_access import (
    end_expired_support_access_job,
)
from app.gateways.worker.periodic.group_conversation_topics import (
    group_conversation_topics_job,
)
from app.gateways.worker.periodic.growth_analytics import (
    purge_web_vitals_job,
    reconcile_product_events_job,
)
from app.gateways.worker.periodic.platform_alerts import platform_alerts_job
from app.gateways.worker.periodic.purge_business_exports import (
    purge_business_exports_job,
)
from app.gateways.worker.periodic.purge_stale_rows import purge_stale_rows_job
from app.gateways.worker.periodic.quality_sampling import quality_sampling_job
from app.gateways.worker.periodic.record_platform_status import (
    record_platform_status_job,
)
from app.gateways.worker.periodic.refresh_client_standings import (
    refresh_client_standings_job,
)
from app.gateways.worker.periodic.refresh_exchange_rates import (
    refresh_exchange_rates_job,
)
from app.gateways.worker.periodic.request_visit_feedback import (
    request_visit_feedback_job,
)
from app.gateways.worker.periodic.retention import retention_purge_job
from app.gateways.worker.periodic.send_subprocessor_notices import (
    send_subprocessor_notices_job,
)
from app.gateways.worker.periodic.send_value_reports import send_value_reports_job
from app.gateways.worker.periodic.sweep_rate_limit_buckets import (
    sweep_rate_limit_buckets_job,
)
from app.gateways.worker.periodic.sweep_stale_inbound_events import (
    sweep_stale_inbound_events_job,
)
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    SEND_PLATFORM_ALERT_JOB,
)
from app.use_cases.admin.security.key_rotation_views import (
    ROTATE_ENCRYPTED_SECRETS_JOB,
)
from app.use_cases.autotests.enqueue_autotest_run_use_case import RUN_AUTOTESTS_JOB
from app.use_cases.knowledge.website_import.start_website_import_use_case import (
    IMPORT_WEBSITE_JOB,
)
from app.use_cases.shared.business_export_queue import BUILD_BUSINESS_EXPORT_JOB
from app.use_cases.voice.recordings.recording_archive_paths import (
    ARCHIVE_CALL_RECORDING_JOB,
)
from app.utilities.calls.text_back_jobs import SEND_TEXT_BACK_JOB
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    PROCESS_INBOUND_MESSAGE_JOB,
    PROCESS_PLATFORM_BOT_UPDATE_JOB,
    PROCESS_POST_CALL_JOB,
)
from app.utilities.memory.summary_jobs import SUMMARIZE_CONVERSATION_JOB
from app.utilities.privacy.processor_erasure_jobs import ERASE_PROCESSOR_COPIES_JOB

MINUTE_SECONDS: int = 60
HOUR_SECONDS: int = 60 * MINUTE_SECONDS
DAY_SECONDS: int = 24 * HOUR_SECONDS

PURGE_EXPIRED_RECORDINGS_JOB: JobName = JobName("purge_expired_recordings")
END_TRIALS_JOB: JobName = JobName("end_trials")
ENFORCE_GRACE_PERIODS_JOB: JobName = JobName("enforce_grace_periods")
CHECK_PACKAGE_USAGE_JOB: JobName = JobName("check_package_usage")
INVOICE_USAGE_OVERAGE_JOB: JobName = JobName("invoice_usage_overage")
SEND_BOOKING_REMINDERS_JOB: JobName = JobName("send_booking_reminders")
FLUSH_LLM_TRACES_JOB: JobName = JobName("flush_llm_traces")
PURGE_FINISHED_JOBS_JOB: JobName = JobName("purge_finished_jobs")


class GatewaysContainer(containers.DeclarativeContainer):
    """
    Transport entry points built from operators. The HTTP routers are
    assembled by `app.gateways.http.router_assembly`; the background worker
    (time-triggered transport) is wired here.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    operators: OperatorsContainer = composed_container_edge(OperatorsContainer)  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # Periodic jobs in the order they run within a tick, each once per
    # period (day or interval) across workers: trials end before grace
    # periods are enforced, so an expired trial and its grace period are
    # handled in the same hour; minutes above the package are billed before
    # the grace job looks for unpaid bills.
    periodic_jobs: List = List(
        Factory(
            PeriodicJobSpec,
            name=PURGE_EXPIRED_RECORDINGS_JOB,
            interval_seconds=JobIntervalSeconds(DAY_SECONDS),
            operator=operators.compliance.purge_expired_recordings_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=END_TRIALS_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.end_trials_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=INVOICE_USAGE_OVERAGE_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.invoice_usage_overage_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=ENFORCE_GRACE_PERIODS_JOB,
            interval_seconds=JobIntervalSeconds(HOUR_SECONDS),
            operator=operators.billing.enforce_grace_periods_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=CHECK_PACKAGE_USAGE_JOB,
            interval_seconds=JobIntervalSeconds(DAY_SECONDS),
            operator=operators.billing.check_package_usage_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=SEND_BOOKING_REMINDERS_JOB,
            interval_seconds=JobIntervalSeconds(15 * MINUTE_SECONDS),
            operator=operators.operations.send_booking_reminders_operator,
        ),
        Factory(
            PeriodicJobSpec,
            name=PURGE_FINISHED_JOBS_JOB,
            interval_seconds=JobIntervalSeconds(DAY_SECONDS),
            operator=operators.platform.purge_finished_jobs_operator,
        ),
        # Each process flushes its own trace buffer, so this one runs in
        # every worker on its interval instead of once per period.
        Factory(
            PeriodicJobSpec,
            name=FLUSH_LLM_TRACES_JOB,
            interval_seconds=JobIntervalSeconds(MINUTE_SECONDS),
            operator=operators.platform.flush_llm_traces_operator,
            is_process_local=True,
        ),
        Factory(
            purge_stale_rows_job, operator=operators.platform.purge_stale_rows_operator
        ),
        Factory(
            refresh_client_standings_job,
            operator=operators.platform.refresh_client_standings_operator,
        ),
        Factory(
            sweep_rate_limit_buckets_job,
            operator=operators.platform.sweep_rate_limit_buckets_operator,
        ),
        # The inbox's sweeper: lost jobs queued again, unanswered messages
        # handed to staff.
        Factory(
            sweep_stale_inbound_events_job,
            operator=operators.channels.sweep_stale_inbound_events_operator,
        ),
        # The owners' digests and monthly reports (09:00 business time).
        Factory(
            send_value_reports_job, operator=operators.value.send_value_reports_operator
        ),
        # What customers ask about, grouped once a night (Overview card).
        Factory(
            group_conversation_topics_job,
            operator=operators.value.group_conversation_topics_operator,
        ),
        # The judge scores a cost-capped sample of real conversations daily.
        Factory(
            quality_sampling_job,
            operator=operators.platform_ops.sample_conversation_quality_operator,
        ),
        # Customers asked how their visit went (Settings → Reviews).
        Factory(
            request_visit_feedback_job,
            operator=operators.feedback.request_visit_feedback_operator,
        ),
        # The NBG's and ECB's rates of the day, as dated rows.
        Factory(
            refresh_exchange_rates_job,
            operator=operators.billing.refresh_exchange_rates_operator,
        ),
        # Growth analytics: Web Vitals kept 90 days; missing steps derived.
        Factory(
            purge_web_vitals_job, operator=operators.analytics.purge_web_vitals_operator
        ),
        Factory(
            reconcile_product_events_job,
            operator=operators.analytics.reconcile_product_events_operator,
        ),
        # Activation: milestones announced, nudges to stuck owners.
        Factory(
            notice_milestones_job, operator=operators.setup.notice_milestones_operator
        ),
        Factory(
            send_activation_nudges_job,
            operator=operators.setup.send_activation_nudges_operator,
        ),
        # The platform watching itself (docs/operations/slo.md).
        Factory(
            platform_alerts_job,
            operator=operators.platform_ops.check_platform_alerts_operator,
        ),
        Factory(
            check_channel_credentials_job,
            operator=operators.platform_ops.check_channel_credentials_operator,
        ),
        # The status page's daily history (1111).
        Factory(
            record_platform_status_job,
            operator=operators.platform_ops.record_platform_status_operator,
        ),
        # Platform support's time-boxed access closed in the audit log.
        Factory(
            end_expired_support_access_job,
            operator=operators.security.end_expired_support_access_operator,
        ),
        # Archives of full exports deleted once their link ran out.
        Factory(
            purge_business_exports_job,
            operator=operators.privacy.purge_business_exports_operator,
        ),
        Factory(
            retention_purge_job, operator=operators.privacy.retention_purge_operator
        ),
        Factory(  # Sub-processor changes told 30 days ahead (DPA 8.3).
            send_subprocessor_notices_job,
            operator=operators.legal.send_subprocessor_notices_operator,
        ),
    )
    # Handlers of queued jobs by job name (the queue is filled by use cases
    # through the job queue facilitator).
    queued_job_operators: Dict = Dict(
        {
            RUN_AUTOTESTS_JOB: operators.assistants.run_queued_autotests_operator,
            # The inbox: webhook messages answered by the worker.
            PROCESS_INBOUND_MESSAGE_JOB: (
                operators.channels.process_inbound_message_operator
            ),
            PROCESS_PLATFORM_BOT_UPDATE_JOB: (
                operators.channels.process_platform_bot_update_operator
            ),
            PROCESS_POST_CALL_JOB: operators.conversations.process_post_call_operator,
            # A finished call's recording moved into the EU object storage.
            ARCHIVE_CALL_RECORDING_JOB: (
                operators.conversations.archive_call_recording_operator
            ),
            # The outbox: replies and staff notifications sent with retries.
            DELIVER_OUTBOUND_JOB: operators.channels.deliver_outbound_operator,
            # A caller who did not get through: their WhatsApp or SMS.
            SEND_TEXT_BACK_JOB: operators.calls.send_text_back_operator,
            # A full export of a business written into its archive.
            BUILD_BUSINESS_EXPORT_JOB: operators.privacy.run_business_export_operator,
            # A business's website read into knowledge drafts.
            IMPORT_WEBSITE_JOB: operators.knowledge.run_website_import_operator,
            # Every stored secret sealed again with the current key.
            ROTATE_ENCRYPTED_SECRETS_JOB: (
                operators.security.rotate_encrypted_secrets_operator
            ),
            # A platform alert to the team's chats and inboxes.
            SEND_PLATFORM_ALERT_JOB: (
                operators.platform_ops.send_platform_alert_operator
            ),
            # A quiet conversation summarized for the customer memory.
            SUMMARIZE_CONVERSATION_JOB: operators.memory.summarize_conversation_operator,  # noqa: E501
            ERASE_PROCESSOR_COPIES_JOB: operators.privacy.erase_copies_operator,
        }
    )
    # The pulse of this worker process (GET /readyz reports its age).
    worker_heartbeat_recorder: Factory[WorkerHeartbeatRecorder] = Factory(
        WorkerHeartbeatRecorder,
        heartbeat_repo=repositories.worker_heartbeat_repo,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
        release=config.app_settings.provided.release_version,
    )
    background_worker: Factory[BackgroundWorker] = Factory(
        BackgroundWorker,
        periodic_jobs=periodic_jobs,
        queued_job_operators=queued_job_operators,
        job_repo=repositories.queued_job_repo,
        periodic_run_repo=repositories.periodic_job_run_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        error_reporter=facilitators.error_reporter,
        poll_seconds=config.app_settings.provided.worker_poll_seconds,
        storage_scope=utilities.storage_scope,
        job_wakeup=adapters.job_wakeup,
        lane_concurrency=config.app_settings.provided.worker_lane_concurrency,
        job_monitor=facilitators.job_monitor,
        heartbeat_recorder=worker_heartbeat_recorder,
        inbound_poll_seconds=config.app_settings.provided.worker_inbound_poll_seconds,
    )
