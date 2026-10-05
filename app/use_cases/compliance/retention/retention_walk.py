"""Keyset walks of the retention purge: one batch of records at a time."""

from collections.abc import Callable, Iterator

from app.schemas.typings.privacy.constrained_integers import RetentionBatchSize

# Records one read of the purge holds in memory.
RETENTION_BATCH_SIZE: RetentionBatchSize = RetentionBatchSize(500)


def walk_batches[Record](
    read_batch: Callable[[Record | None], list[Record]],
    size: RetentionBatchSize = RETENTION_BATCH_SIZE,
) -> Iterator[Record]:
    """
    Every record `read_batch` returns, batch after batch: each batch starts
    after the last record of the one before, and a short batch is the last.
    """

    after: Record | None = None
    while True:
        batch: list[Record] = read_batch(after)
        yield from batch
        if len(batch) < int(size):
            return

        after = batch[-1]
