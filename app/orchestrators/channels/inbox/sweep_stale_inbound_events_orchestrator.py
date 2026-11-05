import logging

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.inbox_sweep import InboundEventHandoffMark, UnansweredInboundEvent
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount

logger: logging.Logger = logging.getLogger(__name__)


class SweepStaleInboundEventsOrchestrator(OrchestratorContract[JobTick, JobReport]):
    """
    `sweep_stale_inbound_events`: no inbox event is stranded. Events whose
    job was lost (a crash between storing and queuing on an older release,
    a job discarded by hand) get their job again; a customer message the
    assistant gave up on goes to a person through a handoff an hour later,
    and is marked so it is handed off once (marked after the handoff, so
    a sweep that stops between the two finds the conversation handed off
    and only marks it). The report counts both.
    """

    def __init__(
        self,
        requeue_stale_inbound_events: UseCaseContract[JobTick, ProcessedItemCount],
        collect_unanswered_inbound_events: UseCaseContract[
            JobTick, list[UnansweredInboundEvent]
        ],
        handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
        mark_inbound_event_handed_off: UseCaseContract[
            InboundEventHandoffMark, InboundEventDocument | None
        ],
    ) -> None:
        self._requeue_stale_inbound_events: UseCaseContract[
            JobTick, ProcessedItemCount
        ] = requeue_stale_inbound_events
        self._collect_unanswered_inbound_events: UseCaseContract[
            JobTick, list[UnansweredInboundEvent]
        ] = collect_unanswered_inbound_events
        self._handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult] = (
            handoff_to_human
        )
        self._mark_inbound_event_handed_off: UseCaseContract[
            InboundEventHandoffMark, InboundEventDocument | None
        ] = mark_inbound_event_handed_off

    def execute(self, input_data: JobTick) -> JobReport:
        requeued: ProcessedItemCount = self._requeue_stale_inbound_events.run(
            input_data
        )
        handed_off: int = 0
        for unanswered in self._collect_unanswered_inbound_events.run(input_data):
            if unanswered.handoff is not None:
                self._handoff_to_human.run(unanswered.handoff)
                handed_off += 1

            self._mark_inbound_event_handed_off.run(
                InboundEventHandoffMark(
                    event_id=unanswered.event_id,
                    business_id=unanswered.business_id,
                )
            )

        if handed_off:
            logger.warning(
                "The inbox sweep handed %d unanswered message(s) to staff.",
                handed_off,
            )

        return JobReport(processed_count=ProcessedItemCount(int(requeued) + handed_off))
