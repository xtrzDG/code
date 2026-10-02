from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token

from app.contracts.storage import StorageScopeContract
from app.schemas.dto.storage import StorageScope
from app.schemas.typings.businesses.prefixed_id import BusinessId


class StorageScopeContext(StorageScopeContract):
    """
    Storage scope kept in a context variable, fail-closed.

    Each request, job or thread sees its own scope: asyncio tasks and
    `contextvars.copy_context()` inherit it, a new `threading.Thread` starts
    unscoped. Unscoped code cannot touch tenant collections at all: it must
    enter `scoped_to_business(...)` or, explicitly, `platform_wide()`. Scopes
    nest and are restored on exit, also on errors.
    """

    def __init__(self) -> None:
        self._platform_scope: StorageScope = StorageScope.platform_wide()
        self._unscoped: StorageScope = StorageScope.unscoped()
        self._current_scope: ContextVar[StorageScope] = ContextVar(
            "storage_scope",
            default=self._unscoped,
        )

    def current(self) -> StorageScope:
        return self._current_scope.get()

    @contextmanager
    def scoped_to_business(self, business_id: BusinessId) -> Generator[StorageScope]:
        with self._entered(StorageScope.for_business(business_id)) as scope:
            yield scope

    @contextmanager
    def platform_wide(self) -> Generator[StorageScope]:
        with self._entered(self._platform_scope) as scope:
            yield scope

    @contextmanager
    def _entered(self, scope: StorageScope) -> Generator[StorageScope]:
        token: Token[StorageScope] = self._current_scope.set(scope)
        try:
            yield scope
        finally:
            self._current_scope.reset(token)
