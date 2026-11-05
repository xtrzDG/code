"""
Every business of the platform, a keyset batch at a time.

Periodic jobs and platform views that must look at each business walk
them with `walk_businesses`: the batches come from the database in the
order the businesses were created (`BusinessRepoContract.list_batch`), so
a job holds one batch in memory and each read costs the same however many
businesses there are. A business created during the walk is met at its
end; the walk never repeats or skips one.
"""

from collections.abc import Iterator

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.businesses.constrained_integers import BusinessBatchSize
from app.schemas.typings.businesses.prefixed_id import BusinessId

BUSINESS_BATCH_SIZE: BusinessBatchSize = BusinessBatchSize(200)


def walk_businesses(
    business_repo: BusinessRepoContract,
    batch_size: BusinessBatchSize = BUSINESS_BATCH_SIZE,
) -> Iterator[BusinessDocument]:
    """Every business, in the order they were created."""

    after: BusinessId | None = None
    while True:
        batch: list[BusinessDocument] = business_repo.list_batch(after, batch_size)
        yield from batch
        if len(batch) < int(batch_size):
            return

        after = batch[-1].id
