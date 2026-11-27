"""
The periodic jobs the worker built from the real container registers, in
the order they run within a tick, with their intervals in seconds
(`test_worker.py`).
"""

from app.containers.billing_jobs import (
    CHECK_PACKAGE_USAGE_JOB,
    END_TRIALS_JOB,
    ENFORCE_GRACE_PERIODS_JOB,
    INVOICE_USAGE_OVERAGE_JOB,
)
from app.containers.periodic_jobs import (
    FLUSH_LLM_TRACES_JOB,
    PURGE_EXPIRED_RECORDINGS_JOB,
    PURGE_FINISHED_JOBS_JOB,
    SEND_BOOKING_REMINDERS_JOB,
)
from app.gateways.worker.periodic.activation_follow_up import (
    NOTICE_MILESTONES_JOB,
    SEND_ACTIVATION_NUDGES_JOB,
)
from app.gateways.worker.periodic.business_closure_jobs import (
    OFFBOARD_UNPAID_BUSINESSES_JOB,
    QUEUE_BUSINESS_DELETIONS_JOB,
    REAPPLY_CONTACT_ERASURES_JOB,
    REAPPLY_DELETION_LEDGER_JOB,
)
from app.gateways.worker.periodic.calendar_sync import SYNC_CALENDARS_JOB
from app.gateways.worker.periodic.channel_credentials import (
    CHECK_CHANNEL_CREDENTIALS_JOB,
    REFRESH_WHATSAPP_TOKENS_JOB,
)
from app.gateways.worker.periodic.critical_clients_digest import (
    CRITICAL_CLIENTS_DIGEST_JOB,
)
from app.gateways.worker.periodic.end_expired_support_access import (
    END_EXPIRED_SUPPORT_ACCESS_JOB,
)
from app.gateways.worker.periodic.group_conversation_topics import (
    GROUP_CONVERSATION_TOPICS_JOB,
)
from app.gateways.worker.periodic.growth_analytics import (
    PURGE_WEB_VITALS_JOB,
    RECONCILE_PRODUCT_EVENTS_JOB,
)
from app.gateways.worker.periodic.growth_jobs import (
    EXPIRE_WAITLIST_OFFERS_JOB,
    RUN_REBOOKING_CAMPAIGNS_JOB,
    SWEEP_DEPOSITS_JOB,
)
from app.gateways.worker.periodic.phone_number_jobs import (
    BILL_PHONE_NUMBER_RENTALS_JOB,
    MAINTAIN_PHONE_NUMBERS_JOB,
)
from app.gateways.worker.periodic.platform_alerts import PLATFORM_ALERTS_JOB
from app.gateways.worker.periodic.purge_business_exports import (
    PURGE_BUSINESS_EXPORTS_JOB,
)
from app.gateways.worker.periodic.purge_expired_audit_log import (
    PURGE_EXPIRED_AUDIT_LOG_JOB,
)
from app.gateways.worker.periodic.purge_idempotency_keys import (
    PURGE_IDEMPOTENCY_KEYS_JOB,
)
from app.gateways.worker.periodic.purge_stale_rows import PURGE_STALE_ROWS_JOB
from app.gateways.worker.periodic.purge_webhook_deliveries import (
    PURGE_WEBHOOK_DELIVERIES_JOB,
)
from app.gateways.worker.periodic.quality_sampling import QUALITY_SAMPLING_JOB
from app.gateways.worker.periodic.reconcile_payments import RECONCILE_PAYMENTS_JOB
from app.gateways.worker.periodic.record_platform_status import (
    RECORD_PLATFORM_STATUS_JOB,
)
from app.gateways.worker.periodic.record_service_levels import RECORD_SLI_JOB
from app.gateways.worker.periodic.refresh_client_standings import (
    REFRESH_CLIENT_STANDINGS_JOB,
)
from app.gateways.worker.periodic.refresh_exchange_rates import (
    REFRESH_EXCHANGE_RATES_JOB,
)
from app.gateways.worker.periodic.request_visit_feedback import (
    REQUEST_VISIT_FEEDBACK_JOB,
)
from app.gateways.worker.periodic.resync_voice_agents import RESYNC_VOICE_AGENTS_JOB
from app.gateways.worker.periodic.retention import PURGE_EXPIRED_PERSONAL_DATA_JOB
from app.gateways.worker.periodic.run_data_tasks import RUN_DATA_TASKS_JOB
from app.gateways.worker.periodic.send_subprocessor_notices import (
    SEND_SUBPROCESSOR_NOTICES_JOB,
)
from app.gateways.worker.periodic.send_value_reports import SEND_VALUE_REPORTS_JOB
from app.gateways.worker.periodic.subscription_lifecycle_jobs import (
    RETRY_FAILED_PAYMENTS_JOB,
    RUN_SUBSCRIPTION_PAUSES_JOB,
    SEND_WIN_BACK_MESSAGES_JOB,
)
from app.gateways.worker.periodic.sweep_rate_limit_buckets import (
    SWEEP_RATE_LIMIT_BUCKETS_JOB,
)
from app.gateways.worker.periodic.sweep_stale_inbound_events import (
    SWEEP_STALE_INBOUND_EVENTS_JOB,
)
from app.gateways.worker.periodic.verify_audit_chain import VERIFY_AUDIT_CHAIN_JOB
from app.schemas.typings.platform.constrained_strings import JobName

REGISTERED_PERIODIC_JOBS: list[tuple[JobName, int]] = [
    (PURGE_EXPIRED_RECORDINGS_JOB, 86_400),
    (END_TRIALS_JOB, 3_600),
    (INVOICE_USAGE_OVERAGE_JOB, 3_600),
    (BILL_PHONE_NUMBER_RENTALS_JOB, 3_600),
    (RUN_SUBSCRIPTION_PAUSES_JOB, 3_600),
    (RETRY_FAILED_PAYMENTS_JOB, 3_600),
    (ENFORCE_GRACE_PERIODS_JOB, 3_600),
    (CHECK_PACKAGE_USAGE_JOB, 86_400),
    (RECONCILE_PAYMENTS_JOB, 86_400),
    (SEND_BOOKING_REMINDERS_JOB, 900),
    (SYNC_CALENDARS_JOB, 300),
    (MAINTAIN_PHONE_NUMBERS_JOB, 300),
    (PURGE_FINISHED_JOBS_JOB, 86_400),
    (FLUSH_LLM_TRACES_JOB, 60),
    (PURGE_STALE_ROWS_JOB, 86_400),
    (REFRESH_CLIENT_STANDINGS_JOB, 900),
    (SWEEP_RATE_LIMIT_BUCKETS_JOB, 600),
    (SWEEP_STALE_INBOUND_EVENTS_JOB, 300),
    (SEND_VALUE_REPORTS_JOB, 3_600),
    (GROUP_CONVERSATION_TOPICS_JOB, 3_600),
    (QUALITY_SAMPLING_JOB, 86_400),
    (REQUEST_VISIT_FEEDBACK_JOB, 600),
    (REFRESH_EXCHANGE_RATES_JOB, 21_600),
    (PURGE_WEB_VITALS_JOB, 86_400),
    (RECONCILE_PRODUCT_EVENTS_JOB, 86_400),
    (NOTICE_MILESTONES_JOB, 600),
    (SEND_ACTIVATION_NUDGES_JOB, 3_600),
    (PLATFORM_ALERTS_JOB, 300),
    (CHECK_CHANNEL_CREDENTIALS_JOB, 3_600),
    (REFRESH_WHATSAPP_TOKENS_JOB, 21_600),
    (CRITICAL_CLIENTS_DIGEST_JOB, 86_400),
    (RECORD_PLATFORM_STATUS_JOB, 300),
    (RECORD_SLI_JOB, 300),
    (END_EXPIRED_SUPPORT_ACCESS_JOB, 600),
    (PURGE_BUSINESS_EXPORTS_JOB, 3600),
    (PURGE_EXPIRED_PERSONAL_DATA_JOB, 86_400),
    (PURGE_IDEMPOTENCY_KEYS_JOB, 3_600),
    (VERIFY_AUDIT_CHAIN_JOB, 86_400),
    (PURGE_EXPIRED_AUDIT_LOG_JOB, 86_400),
    (SEND_SUBPROCESSOR_NOTICES_JOB, 86_400),
    (EXPIRE_WAITLIST_OFFERS_JOB, 60),
    (RUN_REBOOKING_CAMPAIGNS_JOB, 3_600),
    (SWEEP_DEPOSITS_JOB, 60),
    (SEND_WIN_BACK_MESSAGES_JOB, 3_600),
    (RUN_DATA_TASKS_JOB, 300),
    (PURGE_WEBHOOK_DELIVERIES_JOB, 86_400),
    (RESYNC_VOICE_AGENTS_JOB, 3_600),
    (QUEUE_BUSINESS_DELETIONS_JOB, 3_600),
    (OFFBOARD_UNPAID_BUSINESSES_JOB, 86_400),
    (REAPPLY_DELETION_LEDGER_JOB, 86_400),
    (REAPPLY_CONTACT_ERASURES_JOB, 86_400),
]
