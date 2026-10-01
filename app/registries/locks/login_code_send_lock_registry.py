import threading
from contextlib import AbstractContextManager

from app.contracts.registries import LoginCodeSendLockRegistryContract


class LoginCodeSendLockRegistry(LoginCodeSendLockRegistryContract):
    """
    One lock for the check-and-reserve step of login code sends.

    It protects one process only (WEB_CONCURRENCY defaults to 1); running
    several workers or instances also needs a database-level guard (an
    advisory lock) around the same section.
    """

    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()

    def lock(self) -> AbstractContextManager[object]:
        return self._lock
