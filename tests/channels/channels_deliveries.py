"""
The channels testbed's inbox and outbox: the webhooks' intake, the worker's
jobs (process a message, the platform bot, a finished call; deliver an
outbox message) and a background worker that runs them on demand.
"""

from app.contracts.jobs import QueuedJobOperator
from app.contracts.orchestrator_contract import OrchestratorContract
from app.gateways.worker.background_worker import BackgroundWorker, WorkerTickReport
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.channels.inbox.process_inbound_message_orchestrator import (
    ProcessInboundMessageOrchestrator,
)
from app.orchestrators.channels.inbox.process_platform_bot_update_orchestrator import (
    ProcessPlatformBotUpdateOrchestrator,
)
from app.orchestrators.channels.inbox.process_post_call_orchestrator import (
    ProcessPostCallOrchestrator,
)
from app.orchestrators.channels.outbox.deliver_outbound_message_orchestrator import (
    DeliverOutboundMessageOrchestrator,
)
from app.orchestrators.channels.post_call_webhook_orchestrator import (
    PostCallWebhookOrchestrator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.voice_webhooks import PostCallWebhookOutcome
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.calls.text_back_jobs import SEND_TEXT_BACK_JOB
from app.utilities.deliveries.delivery_jobs import (
    DELIVER_OUTBOUND_JOB,
    PROCESS_INBOUND_MESSAGE_JOB,
    PROCESS_PLATFORM_BOT_UPDATE_JOB,
    PROCESS_POST_CALL_JOB,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.channels.channels_fakes import (
    RecordingHandoffToHuman,
    RecordingOrchestrator,
)
from tests.channels.channels_media import ChannelsMedia
from tests.platform.worker_fakes import TEST_LANE_CONCURRENCY, RecordingErrorReporter

# Enough ticks to drain chains of jobs (a message, its reply, a retry).
MAX_WORKER_TICKS: int = 20


def as_job_operator(
    orchestrator: OrchestratorContract[QueuedJobInput, JobReport],
) -> QueuedJobOperator:
    return PipelineOperator(OrchestratorPipeline(orchestrator))


class ChannelsDeliveries(ChannelsMedia):
    """The worker's side: processing inbox events and sending the outbox."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__(settings)
        self.handoffs_to_human = RecordingHandoffToHuman()
        # What the worker's post-call flow made of each processed report.
        self.post_call_outcomes: list[PostCallWebhookOutcome] = []
        self.worker_errors = RecordingErrorReporter()
        self.worker: BackgroundWorker = self.build_worker()

    def job_operators(self) -> dict[JobName, QueuedJobOperator]:
        return {
            PROCESS_INBOUND_MESSAGE_JOB: as_job_operator(
                ProcessInboundMessageOrchestrator(
                    self.claim_inbound_event,
                    self.recall_inbound_reply,
                    self.pipeline,
                    self.finish_inbound_event,
                    self.release_inbound_event,
                    self.read_inbound_attachments,
                )
            ),
            PROCESS_PLATFORM_BOT_UPDATE_JOB: as_job_operator(
                ProcessPlatformBotUpdateOrchestrator(
                    self.claim_inbound_event,
                    self.handle_platform_bot_update,
                    self.finish_inbound_event,
                    self.release_inbound_event,
                )
            ),
            PROCESS_POST_CALL_JOB: as_job_operator(
                ProcessPostCallOrchestrator(
                    self.claim_inbound_event,
                    RecordingOrchestrator(
                        PostCallWebhookOrchestrator(
                            self.read_accepted_post_call,
                            self.record_finished_call,
                            self.post_call_follow_ups(),
                        ),
                        self.post_call_outcomes,
                    ),
                    self.finish_inbound_event,
                    self.release_inbound_event,
                )
            ),
            DELIVER_OUTBOUND_JOB: as_job_operator(
                DeliverOutboundMessageOrchestrator(
                    self.take_due_outbound_message,
                    self.send_outbound_message,
                    self.record_outbound_attempt,
                    self.build_undelivered_reply_handoff,
                    self.handoffs_to_human,
                )
            ),
            SEND_TEXT_BACK_JOB: as_job_operator(
                UseCaseOrchestrator(self.send_text_back)
            ),
        }

    def build_worker(self) -> BackgroundWorker:
        """A worker over the testbed's queue (a fresh one: a restart)."""

        return BackgroundWorker(
            periodic_jobs=[],
            queued_job_operators=self.job_operators(),
            job_repo=self.jobs.job_repo,
            periodic_run_repo=self.jobs.periodic_run_repo,
            wall_clock=self.wall_clock,
            error_reporter=self.worker_errors,
            poll_seconds=WorkerPollSeconds(5),
            storage_scope=StorageScopeContext(),
            job_wakeup=self.jobs.job_wakeup,
            lane_concurrency=TEST_LANE_CONCURRENCY,
        )

    def run_worker(self) -> list[WorkerTickReport]:
        """Ticks until no job is due now (later retries stay queued)."""

        reports: list[WorkerTickReport] = []
        for _ in range(MAX_WORKER_TICKS):
            report: WorkerTickReport = self.worker.run_once()
            reports.append(report)
            if int(report.queued_runs) == 0:
                break

        return reports
