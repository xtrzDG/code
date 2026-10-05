"""One storage transaction for a block of a use case, where there is one."""

from contextlib import AbstractContextManager, nullcontext

from app.contracts.storage import StorageReadSessionContract, StorageUnitOfWorkContract


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


def in_read_session(
    read_session: StorageReadSessionContract | None,
) -> AbstractContextManager[None]:
    """
    The block's reads as one read session on Postgres (one transaction, one
    statement per read). In memory (no read session) the block runs as it is.
    """

    if read_session is None:
        return nullcontext()

    return read_session.read_session()
