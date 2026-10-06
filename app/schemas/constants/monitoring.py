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
    model calls, the failed ones among them, and login codes a platform cap
    refused.
    """

    LLM_CALL = "llm_call"
    LLM_ERROR = "llm_error"
    OTP_CAP_TRIP = "otp_cap_trip"


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
