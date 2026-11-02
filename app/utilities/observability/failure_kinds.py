"""
Which store an error comes from, for the `storage_errors` platform alert
(LOG-04): the database when a psycopg error lies underneath (the storage
adapters translate it and keep it as the cause), the object storage when
it was raised in the object storage client. Every other error is none of
them. The chain of causes is walked a few links deep, never in a loop.
"""

from enum import StrEnum
from types import TracebackType

MAX_CHAIN_LINKS: int = 8
DATABASE_MODULE_PREFIX: str = "psycopg"
OBJECT_STORAGE_MODULE_PREFIX: str = "app.clients.object_storage"


class StoreFailureKind(StrEnum):
    """The store an error comes from (never stored: a signal is counted)."""

    DATABASE = "database"
    OBJECT_STORAGE = "object_storage"


def store_failure_of(error: BaseException) -> StoreFailureKind | None:
    """The store `error` (or a cause of it) comes from; None for any other."""

    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen and len(seen) < MAX_CHAIN_LINKS:
        seen.add(id(current))
        if type(current).__module__.startswith(DATABASE_MODULE_PREFIX):
            return StoreFailureKind.DATABASE
        if raised_in(current.__traceback__, OBJECT_STORAGE_MODULE_PREFIX):
            return StoreFailureKind.OBJECT_STORAGE
        current = current.__cause__ or current.__context__

    return None


def raised_in(trace: TracebackType | None, module_prefix: str) -> bool:
    """Whether the innermost frame of a traceback is in a module of the prefix."""

    innermost: TracebackType | None = trace
    while innermost is not None and innermost.tb_next is not None:
        innermost = innermost.tb_next
    if innermost is None:
        return False

    module: object = innermost.tb_frame.f_globals.get("__name__")
    return isinstance(module, str) and module.startswith(module_prefix)
