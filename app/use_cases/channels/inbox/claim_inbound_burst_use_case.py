import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundEventClaim
from app.schemas.dto.inbound_bursts import InboundBurst
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import (
    MessageCoalesceSeconds,
)
from app.schemas.typings.deliveries.prefixed_id import InboundEventId
from app.use_cases.channels.inbox.claim_inbound_event_use_case import (
    build_inbound_message,
    serial_key_of,
)
from app.use_cases.shared.inbox_queue import queue_inbound_job
from app.utilities.deliveries.delivery_jobs import decode_inbound_event_payload
from app.utilities.deliveries.inbound_bursts import (
    burst_answer_at,
    burst_window,
    is_customer_event,
    select_burst,
)
from app.utilities.deliveries.inbound_claims import (
    is_inbound_event_finished,
    is_inbound_event_held_by_another,
    take_inbound_event,
)
from app.utilities.observability.log_formatting import log_fields

logger: logging.Logger = logging.getLogger(__name__)


class ClaimInboundBurstUseCase(UseCaseContract[QueuedJobInput, InboundBurst | None]):
    """
    Take the customer messages a `process_inbound_message` job answers.

    Quick messages in a row get one reply: the job's message and the same
    customer's other unanswered ones (`inbound_bursts`) are answered at
    once when the newest reads as a finished sentence, else once the
    customer has been quiet for MESSAGE_COALESCE_SECONDS (1.5 s on
    Telegram; 0 turns grouping off: every message is answered on its own,
    at once). Until then the job queues itself again for that moment (the
    queue wakes its lane exactly then) and nothing is taken (the inbox is
    not changed). When it is time, every message of the burst is held by
    this worker until its lease ends; a message another worker took
    meanwhile is left to it. The first take of each message records how
    long it waited since it was queued (`queue_to_claim_ms`, also logged).

    None when there is nothing to do: the job's message is finished or gone,
    or another processing still holds it (the job comes back when that
    lease ends, so a crashed turn is processed again). Messages this very
    job held on an attempt whose worker died are taken over at once.
    """

    def __init__(
        self,
        inbound_event_repo: InboundEventRepoContract,
        job_queue: JobQueueFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        coalesce_seconds: MessageCoalesceSeconds,
    ) -> None:
        self._inbound_event_repo: InboundEventRepoContract = inbound_event_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._coalesce_seconds: MessageCoalesceSeconds = coalesce_seconds

    def run(self, input_data: QueuedJobInput) -> InboundBurst | None:
        event_id: InboundEventId = decode_inbound_event_payload(input_data.payload)
        now: Microseconds = self._wall_clock.now_unix()
        trigger: InboundEventDocument | None = self._inbound_event_repo.get(
            input_data.business_id, event_id
        )
        if trigger is None:
            logger.warning("Inbox event %s was not found.", event_id)
            return None

        if is_inbound_event_finished(trigger):
            return None

        if is_inbound_event_held_by_another(trigger, now, input_data.job_id):
            self._come_back(input_data, trigger, trigger.lease_until)
            return None

        burst: list[InboundEventDocument] = self._open_burst(trigger, now, input_data)
        answer_at: Microseconds = burst_answer_at(burst, self._coalesce_seconds)
        if int(self._coalesce_seconds) > 0 and answer_at > now:
            self._come_back(input_data, trigger, answer_at)
            return InboundBurst(trigger=trigger, answer_at=answer_at)

        claims: list[InboundEventClaim] = []
        for event in burst:
            claimed: InboundEventDocument | None = self._inbound_event_repo.update(
                event.business_id,
                event.id,
                lambda current: take_inbound_event(current, now, input_data.job_id),
            )
            if claimed is not None:
                claims.append(
                    InboundEventClaim(
                        event=claimed,
                        message=build_inbound_message(claimed),
                        is_final_attempt=(
                            input_data.is_final_attempt and claimed.id == trigger.id
                        ),
                    )
                )

        taken: InboundEventDocument | None = next(
            (claim.event for claim in claims if claim.event.id == trigger.id), None
        )
        if taken is None:
            return None

        if taken.queue_to_claim_ms is not None:
            logger.info(
                "Customer messages taken to answer",
                extra=log_fields(
                    queue_to_claim_ms=int(taken.queue_to_claim_ms),
                    burst_size=len(claims),
                ),
            )

        return InboundBurst(trigger=trigger, claims=claims)

    def _open_burst(
        self,
        trigger: InboundEventDocument,
        now: Microseconds,
        input_data: QueuedJobInput,
    ) -> list[InboundEventDocument]:
        """The trigger and its customer's other open messages, oldest first."""

        business_id: BusinessId | None = trigger.business_id
        if (
            int(self._coalesce_seconds) == 0
            or business_id is None
            or not is_customer_event(trigger)
        ):
            return [trigger]

        window_start, window_end = burst_window(trigger)
        return select_burst(
            trigger,
            self._inbound_event_repo.list_created_between(
                business_id, window_start, window_end
            ),
            now,
            input_data.job_id,
        )

    def _come_back(
        self,
        input_data: QueuedJobInput,
        trigger: InboundEventDocument,
        run_at: Microseconds | None,
    ) -> None:
        queue_inbound_job(
            self._job_queue,
            trigger,
            input_data.job_name,
            serial_key_of(trigger),
            run_at=run_at,
        )
