from enum import StrEnum


class PlatformAlertCode(StrEnum):
    """
    What the platform alerts job watches (ops/alerts/*.yaml has each rule's
    threshold, window and runbook).

    DEAD_JOBS: queued jobs ran out of attempts. INBOUND_BACKLOG: a customer
    message waits for a worker. OUTBOUND_FAILURES: replies and staff
    notifications fail for good. LLM_ERRORS: model calls fail. HANDOFF_SPIKE:
    far more conversations go to people than usual. TOOL_ERRORS: assistant
    tools fail. STALE_WORKER: a worker of the current release stopped
    beating. OTP_CAP_TRIPS: a platform cap refused login codes.
    QUALITY_DROP: the judge's scores of real conversations fell against the
    week before (production quality). SPEND_SPIKE: today's provider spend
    is far above the daily mean of the week before. SPEND_BUDGET: today's
    provider spend passed 80 % of the platform's daily budget.
    BACKFILL_STALLED: a post-deploy data task has not finished within a
    day of becoming due (docs/operations/deploys.md).
    ANSWER_BUDGET_FAST_BURN, ANSWER_BUDGET_SLOW_BURN: the error budget of
    "answered within 60 s" burns 14.4 times too fast over 1 h and 5 min, or
    6 times over 6 h and 30 min; API_BUDGET_FAST_BURN, API_BUDGET_SLOW_BURN
    the same for API availability (docs/operations/slo.md).
    WORKER_DOWN: no background worker wrote its pulse for five minutes,
    seen from outside the workers too (the API's pipeline watchdog and
    GET /healthz/pipeline): customers' messages are not answered.
    BULK_PERSONAL_DATA: one business exported or erased personal data more
    than 20 times in an hour. TENANT_HOPPING: one platform admin entered or
    changed more than 10 businesses in an hour. FAILED_SIGN_IN_CHECKS: more
    than 50 wrong sign-in codes in an hour for one destination (a phone, an
    e-mail address, a person's second factor). AUDIT_CHAIN_BROKEN: the
    daily check found an audit hash chain broken (an entry changed,
    removed or put in). VOICE_HEALTH: calls of the voice platform's API
    fail, or its finished-call reports stopped while the 7 days before
    expect calls at this time of day. SPEND_BUDGET_STOP: today's provider
    spend reached the share of the daily budget where every assistant
    stops calling the model (PLATFORM_DAILY_SPEND_STOP_PERCENT).
    MISSED_JOB_RUNS: a periodic job has not succeeded within its interval
    and grace (its heartbeat in `periodic_job_heartbeats`, not Sentry).
    PAYMENT_MISMATCH: the daily reconciliation found payments whose status
    at Flitt or Stripe differs from the platform's record.
    WEBHOOK_SIGNATURE_FAILURES: a burst of webhook deliveries refused as
    unsigned, badly signed or stale (a secret out of step, or probing).
    STORAGE_ERRORS: the database or the object storage failed requests and
    jobs. API_LATENCY: too many API requests took longer than 2 s.
    BACKUP_FAILED: the last off-site backup failed, or none succeeded for
    26 hours. TENANT_SMS_VOLUME: a business passed its hourly SMS volume
    (an alert at 60, refused from 200: SMS pumping through a tenant).
    OTP_CONVERSION: most login codes of the last hour were never used
    (SMS pumping through sign-in).
    BOOKING_SPIKE, CANCELLATION_SPIKE: one business got more new bookings,
    or more cancellations, in an hour than its hourly cap of either (fake
    bookings holding every slot, or a mass cancellation). WHATSAPP_QUALITY:
    Meta flagged or downgraded a business's WhatsApp number, lowered a
    template's quality, paused or disabled a template, or moved one into
    the marketing category (the number risks a restriction).
    """

    DEAD_JOBS = "dead_jobs"
    INBOUND_BACKLOG = "inbound_backlog"
    OUTBOUND_FAILURES = "outbound_failures"
    LLM_ERRORS = "llm_errors"
    HANDOFF_SPIKE = "handoff_spike"
    TOOL_ERRORS = "tool_errors"
    STALE_WORKER = "stale_worker"
    OTP_CAP_TRIPS = "otp_cap_trips"
    QUALITY_DROP = "quality_drop"
    SPEND_SPIKE = "spend_spike"
    SPEND_BUDGET = "spend_budget"
    BACKFILL_STALLED = "backfill_stalled"
    ANSWER_BUDGET_FAST_BURN = "answer_budget_fast_burn"
    ANSWER_BUDGET_SLOW_BURN = "answer_budget_slow_burn"
    API_BUDGET_FAST_BURN = "api_budget_fast_burn"
    API_BUDGET_SLOW_BURN = "api_budget_slow_burn"
    WORKER_DOWN = "worker_down"
    BULK_PERSONAL_DATA = "bulk_personal_data"
    TENANT_HOPPING = "tenant_hopping"
    FAILED_SIGN_IN_CHECKS = "failed_sign_in_checks"
    AUDIT_CHAIN_BROKEN = "audit_chain_broken"
    VOICE_HEALTH = "voice_health"
    SPEND_BUDGET_STOP = "spend_budget_stop"
    MISSED_JOB_RUNS = "missed_job_runs"
    PAYMENT_MISMATCH = "payment_mismatch"
    WEBHOOK_SIGNATURE_FAILURES = "webhook_signature_failures"
    STORAGE_ERRORS = "storage_errors"
    API_LATENCY = "api_latency"
    BACKUP_FAILED = "backup_failed"
    TENANT_SMS_VOLUME = "tenant_sms_volume"
    OTP_CONVERSION = "otp_conversion"
    BOOKING_SPIKE = "booking_spike"
    CANCELLATION_SPIKE = "cancellation_spike"
    WHATSAPP_QUALITY = "whatsapp_quality"


class PlatformAlertStatus(StrEnum):
    """Whether a platform alert fires right now or its last episode is over."""

    FIRING = "firing"
    RESOLVED = "resolved"


class AlertUnit(StrEnum):
    """
    What a platform alert's figure and threshold count. RATIO is a rule's
    multiple of a usual level (the handoff spike: three times the hourly
    mean of the week); its checks compare counts.
    """

    COUNT = "count"
    SECONDS = "seconds"
    PERCENT = "percent"
    RATIO = "ratio"


class PlatformSignal(StrEnum):
    """
    Events every process counts in shared windows for the platform alerts:
    model calls, the failed ones among them, login codes a platform cap
    refused, and calls of the voice platform's API (ElevenLabs) with the
    failed ones among them; refused webhook deliveries, requests and jobs
    failed by the database or the object storage, API requests slower
    than 2 s, and SMS of a business past its hourly volume; new bookings
    and cancellations of a business past its hourly cap, and Meta's
    warnings about a WhatsApp number's or template's quality.
    """

    LLM_CALL = "llm_call"
    LLM_ERROR = "llm_error"
    OTP_CAP_TRIP = "otp_cap_trip"
    VOICE_API_CALL = "voice_api_call"
    VOICE_API_ERROR = "voice_api_error"
    WEBHOOK_REFUSED = "webhook_refused"
    DATABASE_ERROR = "database_error"
    OBJECT_STORAGE_ERROR = "object_storage_error"
    SLOW_API_REQUEST = "slow_api_request"
    TENANT_SMS_SURGE = "tenant_sms_surge"
    BOOKING_SURGE = "booking_surge"
    CANCELLATION_SURGE = "cancellation_surge"
    WHATSAPP_QUALITY_DROP = "whatsapp_quality_drop"


class MaintenanceRunKind(StrEnum):
    """What a recorded maintenance run did: an off-site backup or a restore drill."""

    BACKUP = "backup"
    RESTORE_DRILL = "restore_drill"


class MaintenanceRunOutcome(StrEnum):
    """How a backup or a restore drill ended."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AlertNoticeKind(StrEnum):
    """
    Why the team gets a platform alert message: an episode started, it
    still fires after the cooldown, or it is over.
    """

    FIRING = "firing"
    STILL_FIRING = "still_firing"
    RESOLVED = "resolved"


class PlatformMonitor(StrEnum):
    """
    Who watches the platform, each with a mark of its last look
    (`platform_monitors`, 1173): ALERT_CHECKS is the workers'
    `platform_alerts` job (the status page trusts its levels only while
    this mark is fresh); PIPELINE_WATCHDOG is the API's watchdog, whose
    mark also holds the lease of the API instance that leads it.
    """

    ALERT_CHECKS = "alert_checks"
    PIPELINE_WATCHDOG = "pipeline_watchdog"
