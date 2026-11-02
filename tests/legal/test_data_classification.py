"""
The data classification (docs/security/data-classification.md) stays true:
every retention period it states is the one the purge code uses, every
purge job it names exists in the entry-point inventory, every transfer cell
is filled, every vendor of a transfer is in the vendor register, and the
monitoring of the retention job names its real Sentry monitor.
"""

import json

from app.facilitators.observability.sentry_job_monitor_facilitator import (
    monitor_slug,
)
from app.gateways.worker.periodic.retention import PURGE_EXPIRED_PERSONAL_DATA_JOB
from app.schemas.configurations.privacy_settings import (
    DEFAULT_EXPORT_DOWNLOAD_LINK_MINUTES,
    DEFAULT_OFFBOARD_AFTER_DAYS,
)
from app.schemas.domain.business_privacy_settings import (
    DEFAULT_CONVERSATION_RETENTION_DAYS,
    DEFAULT_LLM_TURN_RETENTION_DAYS,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.privacy.constrained_integers import (
    ConversationRetentionDays,
    LlmTurnRetentionDays,
)
from app.use_cases.idempotency.claim_idempotency_key_use_case import (
    IDEMPOTENCY_KEY_LIFETIME,
)
from app.use_cases.jobs.purge_finished_jobs_use_case import (
    FINISHED_JOB_RETENTION_DAYS,
)
from app.use_cases.maintenance.purge_stale_rows_use_case import (
    CHANNEL_RECEIPT_RETENTION_SECONDS,
    DELIVERY_RETENTION_SECONDS,
    MISSED_CALL_RETENTION_SECONDS,
    OTP_CHALLENGE_RETENTION_SECONDS,
)
from app.use_cases.telemetry.purge_web_vitals_use_case import (
    WEB_VITAL_RETENTION_SECONDS,
)
from app.utilities.compliance.audit_retention import MINIMUM_AUDIT_RETENTION_DAYS
from app.utilities.integrations import webhook_schedule
from tests.legal.governance_documents import (
    OPERATIONS,
    missing_paths,
    read,
    section,
    table_rows,
)

CLASSIFICATION: str = "docs/security/data-classification.md"
HOUR: int = 60 * 60
DAY: int = 24 * HOUR
DAYS_PER_YEAR: int = 365
RECORDING_DEFAULT: int = int(
    BusinessDocument.model_fields["recording_retention_days"].default
)


def bound(limit: int | None) -> int:
    """A constrained primitive's bound, which these primitives always set."""

    assert limit is not None
    return limit


# The period each retention row must state, from the constant its purge uses.
EXPECTED_PERIODS: dict[str, str] = {
    "Sign-in-code challenges": f"{OTP_CHALLENGE_RETENTION_SECONDS // HOUR} hours",
    "Second sign-in steps and passkey challenges": (
        f"{OTP_CHALLENGE_RETENTION_SECONDS // HOUR} hours"
    ),
    "Delivery logs (outbox messages)": f"{DELIVERY_RETENTION_SECONDS // DAY} days",
    "Webhook receipts and inbox events": (
        f"{CHANNEL_RECEIPT_RETENTION_SECONDS // DAY} days"
    ),
    "Outbound webhook delivery log": (
        f"{webhook_schedule.DELIVERY_RETENTION_SECONDS // DAY} days"
    ),
    "Missed calls": f"{MISSED_CALL_RETENTION_SECONDS // DAY} days",
    "Conversations, notes, transcripts": (
        f"{bound(ConversationRetentionDays.ge)} days to "
        f"{bound(ConversationRetentionDays.le) // DAYS_PER_YEAR} years; "
        f"{int(DEFAULT_CONVERSATION_RETENTION_DAYS)} days by default"
    ),
    "Records of model calls (and their Langfuse traces)": (
        f"{int(DEFAULT_LLM_TURN_RETENTION_DAYS)} days by default"
    ),
    "Call recordings and files customers sent": f"{RECORDING_DEFAULT} days by default",
    "Full business exports": f"{DEFAULT_EXPORT_DOWNLOAD_LINK_MINUTES} minutes",
    "Idempotency keys": f"{int(IDEMPOTENCY_KEY_LIFETIME) // HOUR} hours",
    "Finished queued jobs": f"{int(FINISHED_JOB_RETENTION_DAYS)} days",
    "Web vitals": f"{WEB_VITAL_RETENTION_SECONDS // DAY} days",
    "Audit log": f"at least {int(MINIMUM_AUDIT_RETENTION_DAYS)} days",
    "A business that stopped paying": f"{DEFAULT_OFFBOARD_AFTER_DAYS} days",
}
# Vendors a transfer cell may name, as the vendor register names them.
VENDORS: tuple[str, ...] = (
    "Meta",
    "Telegram",
    "Twilio",
    "Google",
    "Anthropic",
    "Cloudflare",
    "Stripe",
    "Flitt",
    "Sentry",
    "Langfuse",
    "OpenAI",
    "ElevenLabs",
    "Zadarma",
    "Render",
)
UNFINISHED: tuple[str, ...] = ("[", "to be confirmed", "TBD", "?")


def retention_rows() -> dict[str, list[str]]:
    rows = table_rows(section(read(CLASSIFICATION), "Retention"))
    return {row[0]: row for row in rows}


def category_rows() -> list[list[str]]:
    return table_rows(section(read(CLASSIFICATION), "Categories and where they go"))


def test_every_retention_period_is_the_one_the_code_uses() -> None:
    rows = retention_rows()

    assert bound(LlmTurnRetentionDays.le) == int(DEFAULT_LLM_TURN_RETENTION_DAYS)
    for label, period in EXPECTED_PERIODS.items():
        assert label in rows, f"{CLASSIFICATION} lost the row {label!r}"
        assert period in rows[label][1], (label, rows[label][1], period)


def test_every_purge_job_named_is_a_job_of_the_worker() -> None:
    inventory = json.loads(read("docs/security/entry-points.json"))
    jobs = {str(job["name"]) for job in inventory["periodic_jobs"]} | {
        str(job["name"]) for job in inventory["queued_jobs"]
    }
    named = {
        cell.split("`")[1]
        for row in retention_rows().values()
        for cell in [row[2]]
        if cell.startswith("`") and not cell.startswith("`workshop ")
    }

    assert len(named) >= 8
    assert sorted(named - jobs) == []


def test_every_category_has_its_transfers_filled_in() -> None:
    rows = category_rows()

    assert len(rows) >= 12
    for row in rows:
        assert len(row) == 6 and all(row), row
        assert not any(mark in row[5] for mark in UNFINISHED), row


def test_every_vendor_of_a_transfer_is_in_the_vendor_register() -> None:
    register = {
        row[0].split(" (")[0]
        for row in table_rows(
            section(read("docs/operations/vendor-register.md"), "Register")
        )
    }
    named = {
        vendor
        for row in category_rows()
        for vendor in VENDORS
        if vendor in row[5] or vendor in row[4]
    }

    assert len(named) >= 10
    assert sorted(named - register) == []


def test_the_retention_job_is_watched_through_its_sentry_monitor() -> None:
    watched = section(read(CLASSIFICATION), "Is the retention job running?")

    assert f"`{monitor_slug(PURGE_EXPIRED_PERSONAL_DATA_JOB)}`" in watched
    assert "`periodic_job_runs`" in watched
    assert "`retention_purge`" in watched


def test_the_classification_names_only_paths_that_exist() -> None:
    assert missing_paths(read(CLASSIFICATION), OPERATIONS) == []
