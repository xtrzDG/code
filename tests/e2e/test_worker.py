"""The background worker built from the real container."""

import signal
import threading
from collections.abc import Iterator
from typing import cast

import pytest

from app.containers.periodic_jobs import FLUSH_LLM_TRACES_JOB
from app.contracts.jobs import QueuedJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    SEND_PLATFORM_ALERT_JOB,
)
from app.use_cases.admin.incidents.incident_expansion import EXPAND_INCIDENT_JOB
from app.use_cases.admin.security.key_rotation_views import (
    ROTATE_ENCRYPTED_SECRETS_JOB,
)
from app.use_cases.autotests.enqueue_autotest_run_use_case import RUN_AUTOTESTS_JOB
from app.use_cases.billing.payment_webhook.payment_notification_jobs import (
    APPLY_PAYMENT_NOTIFICATION_JOB,
)
from app.use_cases.compliance.record_contact_erasure_use_case import (
    RECORD_CONTACT_ERASURE_JOB,
)
from app.use_cases.knowledge.website_import.start_website_import_use_case import (
    IMPORT_WEBSITE_JOB,
)
from app.use_cases.shared.business_export_queue import BUILD_BUSINESS_EXPORT_JOB
from app.use_cases.shared.knowledge_index_queue import INDEX_KNOWLEDGE_JOB
from app.use_cases.voice.recordings.recording_archive_paths import (
    ARCHIVE_CALL_RECORDING_JOB,
    DISCARD_CALL_RECORDING_JOB,
)
from app.utilities.business_closures.deletion_jobs import DELETE_BUSINESS_JOB
from app.utilities.calendar_sync.booking_system_jobs import (
    WRITE_BOOKING_SYSTEM_BOOKING_JOB,
)
from app.utilities.calls.text_back_jobs import SEND_TEXT_BACK_JOB
from app.utilities.deliveries.comment_trigger_jobs import PROCESS_COMMENT_TRIGGER_JOB
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    PROCESS_INBOUND_MESSAGE_JOB,
    PROCESS_PLATFORM_BOT_UPDATE_JOB,
    PROCESS_POST_CALL_JOB,
)
from app.utilities.integrations.webhook_jobs import DELIVER_WEBHOOK_JOB
from app.utilities.memory.summary_jobs import SUMMARIZE_CONVERSATION_JOB
from app.utilities.privacy.processor_erasure_jobs import ERASE_PROCESSOR_COPIES_JOB
from app.utilities.waitlist.offer_jobs import OFFER_FREED_PLACE_JOB
from app.worker_main import STOP_SIGNALS, install_stop_signal_handlers, main
from tests.e2e.harness import start_workshop
from tests.e2e.registered_periodic_jobs import REGISTERED_PERIODIC_JOBS


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

    assert [
        (job.name, int(job.interval_seconds)) for job in jobs
    ] == REGISTERED_PERIODIC_JOBS
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
        PROCESS_COMMENT_TRIGGER_JOB,
        APPLY_PAYMENT_NOTIFICATION_JOB,
        ARCHIVE_CALL_RECORDING_JOB,
        DISCARD_CALL_RECORDING_JOB,
        DELIVER_OUTBOUND_JOB,
        SEND_TEXT_BACK_JOB,
        BUILD_BUSINESS_EXPORT_JOB,
        IMPORT_WEBSITE_JOB,
        INDEX_KNOWLEDGE_JOB,
        ROTATE_ENCRYPTED_SECRETS_JOB,
        SEND_PLATFORM_ALERT_JOB,
        SUMMARIZE_CONVERSATION_JOB,
        ERASE_PROCESSOR_COPIES_JOB,
        RECORD_CONTACT_ERASURE_JOB,
        OFFER_FREED_PLACE_JOB,
        EXPAND_INCIDENT_JOB,
        DELIVER_WEBHOOK_JOB,
        WRITE_BOOKING_SYSTEM_BOOKING_JOB,
        DELETE_BUSINESS_JOB,
    ]
    assert (first.periodic_runs, first.queued_runs, first.failures) == (51, 0, 0)
    assert right_after.periodic_runs == 0
    # The trace flush, the end of the waitlist's expired holds and the
    # deposits' holds and reminders.
    assert a_minute_later.periodic_runs == 3
    # Trials, overage, grace periods, reminders, the trace flush, the admin
    # client list standings, the sweep of rate-limit counters, the inbox
    # sweep, the owners' value reports, the customers' topics, the feedback
    # requests, the milestones, the activation nudges, the platform alerts,
    # the Meta token check, the platform status record, the service levels,
    # the end of expired support access, the purge of expired exports, the
    # waitlist's expired holds, the rebooking campaigns, the deposits' holds
    # and reminders, the seasonal pauses, the win-back messages, the retries
    # of declined payments, the post-deploy data tasks, the calendars' busy
    # times, the purge of expired idempotency keys, the voice agents'
    # re-sync, the rented phone numbers' two jobs and the closures whose
    # deletion is due.
    assert (an_hour_later.periodic_runs, an_hour_later.failures) == (32, 0)
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
