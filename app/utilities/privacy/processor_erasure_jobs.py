"""The queued job that deletes copies at a sub-processor, and its batches."""

from collections.abc import Iterator

from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.typings.platform.constrained_strings import JobName

ERASE_PROCESSOR_COPIES_JOB: JobName = JobName("erase_processor_copies")
# References (conversations or calls) one job deletes: a retry repeats at
# most this many requests to the processor.
MAX_REFERENCES_PER_JOB: int = 100


def split_scope(scope: ProcessorErasureScope) -> Iterator[ProcessorErasureScope]:
    """`scope` in batches of at most MAX_REFERENCES_PER_JOB references each."""

    for start in range(0, len(scope.conversation_ids), MAX_REFERENCES_PER_JOB):
        yield scope.model_copy(
            update={
                "conversation_ids": scope.conversation_ids[
                    start : start + MAX_REFERENCES_PER_JOB
                ],
                "provider_call_ids": [],
            }
        )

    for start in range(0, len(scope.provider_call_ids), MAX_REFERENCES_PER_JOB):
        yield scope.model_copy(
            update={
                "conversation_ids": [],
                "provider_call_ids": scope.provider_call_ids[
                    start : start + MAX_REFERENCES_PER_JOB
                ],
            }
        )
