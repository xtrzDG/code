"""
The worker's periodic jobs, in the order they run within a tick, each with
its period and its operator: `GatewaysContainer.periodic_jobs`.
"""

from dependency_injector.providers import Factory, List

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.activation_follow_up import (
    notice_milestones_job,
    send_activation_nudges_job,
)
from app.gateways.worker.periodic.channel_credentials import (
    check_channel_credentials_job,
)
from app.gateways.worker.periodic.critical_clients_digest import (
    critical_clients_digest_job,
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
from app.gateways.worker.periodic.growth_jobs import (
    expire_waitlist_offers_job,
    run_rebooking_campaigns_job,
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
from app.gateways.worker.periodic.run_data_tasks import run_data_tasks_job
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
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

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


def periodic_job_specs(operators: OperatorsContainer) -> List:
    """The periodic jobs, each run by its operator."""

    # Periodic jobs in the order they run within a tick, each once per
    # period (day or interval) across workers: trials end before grace
    # periods are enforced, so an expired trial and its grace period are
    # handled in the same hour; minutes above the package are billed before
    # the grace job looks for unpaid bills.
    return List(
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
            # Customers' reminders go out with the workers that answer them.
            lane=JobLane.OUTBOUND,
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
        # Clients that newly turned critical, once a day to the team's chats.
        Factory(
            critical_clients_digest_job,
            operator=operators.admin_actions.send_critical_clients_digest_operator,
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
        # The waitlist's lapsed holds offered on; the rebooking campaigns.
        Factory(
            expire_waitlist_offers_job,
            operator=operators.growth.expire_waitlist_offers_operator,
        ),
        Factory(
            run_rebooking_campaigns_job,
            operator=operators.growth.run_rebooking_campaigns_operator,
        ),
        # Post-deploy data tasks: migrations and lookup backfills (1164).
        Factory(
            run_data_tasks_job, operator=operators.data_tasks.run_data_tasks_operator
        ),
    )
