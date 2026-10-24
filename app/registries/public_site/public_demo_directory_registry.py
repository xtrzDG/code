import threading
from collections.abc import Sequence

from app.contracts.public_demos import PublicDemoDirectoryRegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId


class PublicDemoDirectoryRegistry(PublicDemoDirectoryRegistryContract):
    """
    The demo businesses visitors of the landing page may chat with: the
    configured ones (PUBLIC_DEMO_BUSINESS_IDS) in their order. In
    development without that setting, the API offers the businesses
    SEED_DEMO_DATA created once seeding has run (`adopt_seeded`); the
    configured list is never replaced. Reads and the one-time adoption are
    serialized by a lock (request threads read while the startup writes).
    """

    def __init__(self, configured_business_ids: Sequence[BusinessId]) -> None:
        self._configured: tuple[BusinessId, ...] = tuple(configured_business_ids)
        self._business_ids: tuple[BusinessId, ...] = self._configured
        self._lock: threading.Lock = threading.Lock()

    def list_business_ids(self) -> list[BusinessId]:
        with self._lock:
            return list(self._business_ids)

    def includes(self, business_id: BusinessId) -> bool:
        with self._lock:
            return business_id in self._business_ids

    def adopt_seeded(self, business_ids: Sequence[BusinessId]) -> None:
        with self._lock:
            if self._configured:
                return

            self._business_ids = tuple(dict.fromkeys(business_ids))
