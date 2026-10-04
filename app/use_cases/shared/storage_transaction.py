"""One storage transaction for a block of a use case, where there is one."""

from contextlib import AbstractContextManager, nullcontext

from app.contracts.storage import StorageUnitOfWorkContract


def in_unit_of_work(
    unit_of_work: StorageUnitOfWorkContract | None,
) -> AbstractContextManager[None]:
    """
    The block as one unit of work on Postgres: its writes commit together
    or not at all. In memory (no unit of work) the block runs as it is.
    """

    if unit_of_work is None:
        return nullcontext()

    return unit_of_work.unit_of_work()
