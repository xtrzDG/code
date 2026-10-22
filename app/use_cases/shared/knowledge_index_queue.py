"""
Asking for a business's knowledge to be indexed again: its aliases in the
business's other languages and, with an embeddings key, the vectors of its
hybrid search. A version's assembly and a confirmed import ask for it; the
worker's `IndexKnowledgeUseCase` does the work.
"""

from app.contracts.jobs import JobQueueFacilitatorContract
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson

INDEX_KNOWLEDGE_JOB: JobName = JobName("index_knowledge")
EMPTY_PAYLOAD: JobPayloadJson = JobPayloadJson("{}")


def queue_knowledge_index(
    job_queue: JobQueueFacilitatorContract, business_id: BusinessId
) -> None:
    """
    Queue the business's indexing job (one at a time per business: a run
    that finds nothing new costs no model call).
    """

    job_queue.enqueue(
        INDEX_KNOWLEDGE_JOB,
        EMPTY_PAYLOAD,
        business_id,
        lane=JobLane.DEFAULT,
        serial_key=JobSerialKey(f"index_knowledge:{business_id}"),
    )
