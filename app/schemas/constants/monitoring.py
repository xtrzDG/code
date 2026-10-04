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
    """

    DEAD_JOBS = "dead_jobs"
    INBOUND_BACKLOG = "inbound_backlog"
    OUTBOUND_FAILURES = "outbound_failures"
    LLM_ERRORS = "llm_errors"
    HANDOFF_SPIKE = "handoff_spike"
    TOOL_ERRORS = "tool_errors"
    STALE_WORKER = "stale_worker"
    OTP_CAP_TRIPS = "otp_cap_trips"


class PlatformAlertStatus(StrEnum):
    """Whether a platform alert fires right now or its last episode is over."""

    FIRING = "firing"
    RESOLVED = "resolved"


class AlertUnit(StrEnum):
    """What a platform alert's figure and threshold count."""

    COUNT = "count"
    SECONDS = "seconds"
    PERCENT = "percent"


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
