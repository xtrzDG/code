"""The background worker built from the real container."""

import signal
import threading
from collections.abc import Iterator
from typing import cast

import pytest

from app.containers.periodic_jobs import (
    CHECK_PACKAGE_USAGE_JOB,
    END_TRIALS_JOB,
    ENFORCE_GRACE_PERIODS_JOB,
    FLUSH_LLM_TRACES_JOB,
    INVOICE_USAGE_OVERAGE_JOB,
    PURGE_EXPIRED_RECORDINGS_JOB,
    PURGE_FINISHED_JOBS_JOB,
    SEND_BOOKING_REMINDERS_JOB,
)
from app.contracts.jobs import QueuedJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.activation_follow_up import (
    NOTICE_MILESTONES_JOB,
    SEND_ACTIVATION_NUDGES_JOB,
)
from app.gateways.worker.periodic.channel_credentials import (
    CHECK_CHANNEL_CREDENTIALS_JOB,
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
)
from app.gateways.worker.periodic.platform_alerts import PLATFORM_ALERTS_JOB
from app.gateways.worker.periodic.purge_business_exports import (
    PURGE_BUSINESS_EXPORTS_JOB,
)
from app.gateways.worker.periodic.purge_stale_rows import PURGE_STALE_ROWS_JOB
from app.gateways.worker.periodic.quality_sampling import QUALITY_SAMPLING_JOB
from app.gateways.worker.periodic.record_platform_status import (
    RECORD_PLATFORM_STATUS_JOB,
)
from app.gateways.worker.periodic.refresh_client_standings import (
    REFRESH_CLIENT_STANDINGS_JOB,
)
from app.gateways.worker.periodic.refresh_exchange_rates import (
    REFRESH_EXCHANGE_RATES_JOB,
)
from app.gateways.worker.periodic.request_visit_feedback import (
    REQUEST_VISIT_FEEDBACK_JOB,
)
from app.gateways.worker.periodic.retention import PURGE_EXPIRED_PERSONAL_DATA_JOB
from app.gateways.worker.periodic.send_subprocessor_notices import (
    SEND_SUBPROCESSOR_NOTICES_JOB,
)
from app.gateways.worker.periodic.send_value_reports import SEND_VALUE_REPORTS_JOB
from app.gateways.worker.periodic.subscription_lifecycle_jobs import (
    RUN_SUBSCRIPTION_PAUSES_JOB,
    SEND_WIN_BACK_MESSAGES_JOB,
)
from app.gateways.worker.periodic.sweep_rate_limit_buckets import (
    SWEEP_RATE_LIMIT_BUCKETS_JOB,
)
from app.gateways.worker.periodic.sweep_stale_inbound_events import (
    SWEEP_STALE_INBOUND_EVENTS_JOB,
)
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
from app.utilities.waitlist.offer_jobs import OFFER_FREED_PLACE_JOB
from app.worker_main import STOP_SIGNALS, install_stop_signal_handlers, main
from tests.e2e.harness import start_workshop


def test_worker_ticks_once_with_every_job_registered() -> None:
    workshop = start_workshop()
    container = workshop.container
    jobs = cast(list[PeriodicJobSpec], container.gateways.periodic_jobs())
    worker = container.gateways.background_worker()

    first = worker.run_once()
    right_after = worker.run_once()
    workshop.clock.advance(60)
    a_minute_later = worker.run_once()
    workshop.clock.advance(60 * 60)
    an_hour_later = worker.run_once()
    after_a_restart = container.gateways.background_worker().run_once()

    assert [(job.name, int(job.interval_seconds)) for job in jobs] == [
        (PURGE_EXPIRED_RECORDINGS_JOB, 86_400),
        (END_TRIALS_JOB, 3_600),
        (INVOICE_USAGE_OVERAGE_JOB, 3_600),
        (RUN_SUBSCRIPTION_PAUSES_JOB, 3_600),
        (ENFORCE_GRACE_PERIODS_JOB, 3_600),
        (CHECK_PACKAGE_USAGE_JOB, 86_400),
        (SEND_BOOKING_REMINDERS_JOB, 900),
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
        (CRITICAL_CLIENTS_DIGEST_JOB, 86_400),
        (RECORD_PLATFORM_STATUS_JOB, 300),
        (END_EXPIRED_SUPPORT_ACCESS_JOB, 600),
        (PURGE_BUSINESS_EXPORTS_JOB, 3600),
        (PURGE_EXPIRED_PERSONAL_DATA_JOB, 86_400),
        (SEND_SUBPROCESSOR_NOTICES_JOB, 86_400),
        (EXPIRE_WAITLIST_OFFERS_JOB, 60),
        (RUN_REBOOKING_CAMPAIGNS_JOB, 3_600),
        (SEND_WIN_BACK_MESSAGES_JOB, 3_600),
    ]
    assert [job.name for job in jobs if job.is_process_local] == [FLUSH_LLM_TRACES_JOB]
    # The worker plays queued autotest runs (concept: assembly autotests run
    # in the background worker).
    queued_operators = cast(
        dict[JobName, QueuedJobOperator], container.gateways.queued_job_operators()
    )
    assert list(queued_operators) == [
        RUN_AUTOTESTS_JOB,
        PROCESS_INBOUND_MESSAGE_JOB,
        PROCESS_PLATFORM_BOT_UPDATE_JOB,
        PROCESS_POST_CALL_JOB,
        ARCHIVE_CALL_RECORDING_JOB,
        DELIVER_OUTBOUND_JOB,
        SEND_TEXT_BACK_JOB,
        BUILD_BUSINESS_EXPORT_JOB,
        IMPORT_WEBSITE_JOB,
        ROTATE_ENCRYPTED_SECRETS_JOB,
        SEND_PLATFORM_ALERT_JOB,
        SUMMARIZE_CONVERSATION_JOB,
        ERASE_PROCESSOR_COPIES_JOB,
        OFFER_FREED_PLACE_JOB,
    ]
    assert (first.periodic_runs, first.queued_runs, first.failures) == (33, 0, 0)
    assert right_after.periodic_runs == 0
    # The trace flush and the end of the waitlist's expired holds.
    assert a_minute_later.periodic_runs == 2
    # Trials, overage, grace periods, reminders, the trace flush, the admin
    # client list standings, the sweep of rate-limit counters, the inbox
    # sweep, the owners' value reports, the customers' topics, the feedback
    # requests, the milestones, the activation nudges, the platform alerts,
    # the Meta token check, the platform status record, the end of expired
    # support access, the purge of expired exports, the waitlist's expired
    # holds, the rebooking campaigns, the seasonal pauses and the win-back
    # messages.
    assert (an_hour_later.periodic_runs, an_hour_later.failures) == (22, 0)
    # A new worker process (a deploy) only flushes its own trace buffer.
    assert (after_a_restart.periodic_runs, after_a_restart.failures) == (1, 0)


@pytest.fixture
def restored_signal_handlers() -> Iterator[None]:
    previous = {
        stop_signal: signal.getsignal(stop_signal) for stop_signal in STOP_SIGNALS
    }
    yield
    for stop_signal, handler in previous.items():
        signal.signal(stop_signal, handler)


@pytest.mark.usefixtures("restored_signal_handlers")
def test_sigterm_asks_the_worker_to_stop() -> None:
    stop_event = threading.Event()

    install_stop_signal_handlers(stop_event)
    signal.raise_signal(signal.SIGTERM)

    assert stop_event.is_set()


@pytest.mark.usefixtures("restored_signal_handlers")
def test_worker_main_runs_until_stopped_and_shuts_down() -> None:
    workshop = start_workshop()
    stop_event = threading.Event()
    stop_event.set()

    exit_code = main(app_container=workshop.container, stop_event=stop_event)

    assert exit_code == 0
