"""
The rules of the inbox's sweeper: when an event counts as stranded, which
job processes each kind of event, and how much one sweep reads.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.delivery_repositories import InboundEventRepoContract
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.typings.deliveries.prefixed_id import InboundEventId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.deliveries.delivery_jobs import (
    PROCESS_INBOUND_MESSAGE_JOB,
    PROCESS_PLATFORM_BOT_UPDATE_JOB,
    PROCESS_POST_CALL_JOB,
    encode_inbound_event_payload,
)
from app.utilities.deliveries.inbound_claims import INBOUND_PROCESSING_LEASE_SECONDS

MICROSECONDS_PER_SECOND: int = 1_000_000
# An event still RECEIVED or PROCESSING twice the processing lease after it
# arrived, with no job waiting or running for it, has lost its job.
STALE_AFTER_SECONDS: int = 2 * INBOUND_PROCESSING_LEASE_SECONDS
# A message the assistant gave up on goes to a person after an hour (the
# job's retries are over by then), if it is at most a day older than that.
UNANSWERED_AFTER_SECONDS: int = 60 * 60
UNANSWERED_LOOKBACK_SECONDS: int = 24 * 60 * 60
# One read of the sweep; a longer backlog is read page by page.
SWEEP_PAGE_SIZE: DocumentQueryLimit = DocumentQueryLimit(200)
MAX_SWEEP_PAGES: int = 10
EVENT_JOBS: dict[InboundEventKind, JobName] = {
    InboundEventKind.CUSTOMER_MESSAGE: PROCESS_INBOUND_MESSAGE_JOB,
    InboundEventKind.PLATFORM_BOT_UPDATE: PROCESS_PLATFORM_BOT_UPDATE_JOB,
    InboundEventKind.VOICE_POST_CALL: PROCESS_POST_CALL_JOB,
}


def seconds_before(now: Microseconds, seconds: int) -> Microseconds:
    return Microseconds(int(now) - seconds * MICROSECONDS_PER_SECOND)


def job_payload(event: InboundEventDocument) -> JobPayloadJson:
    return encode_inbound_event_payload(event.id)


def read_stale_events(
    inbound_event_repo: InboundEventRepoContract,
    status: InboundEventStatus,
    created_before: Microseconds,
    created_from: Microseconds | None = None,
) -> list[InboundEventDocument]:
    """
    The events of a status that arrived in the period, oldest first, page
    by page (at most MAX_SWEEP_PAGES pages). A page starts at the last
    arrival of the one before (events of one webhook share it), so an
    event already read is skipped by its id.
    """

    events: list[InboundEventDocument] = []
    seen: set[InboundEventId] = set()
    start: Microseconds | None = created_from
    for _ in range(MAX_SWEEP_PAGES):
        page: list[InboundEventDocument] = inbound_event_repo.list_stale(
            status, created_before, SWEEP_PAGE_SIZE, created_from=start
        )
        fresh: list[InboundEventDocument] = [
            event for event in page if event.id not in seen
        ]
        events.extend(fresh)
        seen.update(event.id for event in fresh)
        if len(page) < int(SWEEP_PAGE_SIZE) or not fresh:
            break

        start = page[-1].created_at

    return events
