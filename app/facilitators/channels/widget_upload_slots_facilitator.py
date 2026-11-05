"""
How many website chat uploads one API process takes at once: each holds
its file in memory while it is read, checked and stored, so the process
takes MEDIA_MAX_CONCURRENT_UPLOADS of them and one client network at most
a few; the next upload is refused at once (429) rather than queued.
"""

import threading
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager

from app.contracts.widget_upload_slots import WidgetUploadSlotsFacilitatorContract
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.media.constrained_integers import (
    ConcurrentUploadLimit,
    UploadsPerAddressLimit,
)
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.utilities.channels.widget_rate_limits import describe_client_network

# An upload of a few megabytes takes seconds: the widget tries again then.
BUSY_RETRY_SECONDS: int = 5
# A visitor sends one file at a time; an office or a family shares a network.
DEFAULT_UPLOADS_PER_ADDRESS: UploadsPerAddressLimit = UploadsPerAddressLimit(2)
PROCESS_KEY: str = "process"

type SlotKey = tuple[str, str]


class WidgetUploadSlotsFacilitator(WidgetUploadSlotsFacilitatorContract):
    """
    Counts the uploads in progress on this process, in all and per client
    network (thread-safe: the count and the check are one step under a
    lock), and refuses one beyond either limit without waiting for a
    place, so a burst of large files never piles up in memory.
    """

    def __init__(
        self,
        uploads_at_once: ConcurrentUploadLimit,
        uploads_per_address: UploadsPerAddressLimit = DEFAULT_UPLOADS_PER_ADDRESS,
    ) -> None:
        self._uploads_at_once: ConcurrentUploadLimit = uploads_at_once
        self._uploads_per_address: UploadsPerAddressLimit = uploads_per_address
        self._lock: threading.Lock = threading.Lock()
        self._held: Counter[SlotKey] = Counter()

    @contextmanager
    def hold(self, client_ip_address: ClientIpAddress | None) -> Generator[None]:
        keys: list[SlotKey] = self._take(client_ip_address)
        try:
            yield
        finally:
            self._give_back(keys)

    def _take(self, client_ip_address: ClientIpAddress | None) -> list[SlotKey]:
        keys: list[SlotKey] = [(PROCESS_KEY, PROCESS_KEY)]
        if client_ip_address is not None:
            # The network, as the rate limits count it: an IPv6 /64 is one.
            keys.append(("address", describe_client_network(client_ip_address)))

        with self._lock:
            if self._held[keys[0]] >= int(self._uploads_at_once):
                raise too_many_uploads("too_many_uploads_at_once")

            if len(keys) > 1 and self._held[keys[1]] >= int(self._uploads_per_address):
                raise too_many_uploads("too_many_uploads_from_address")

            for key in keys:
                self._held[key] += 1

        return keys

    def _give_back(self, keys: list[SlotKey]) -> None:
        with self._lock:
            for key in keys:
                self._held[key] -= 1
                if self._held[key] <= 0:
                    del self._held[key]


def too_many_uploads(code: str) -> RateLimitedError:
    return RateLimitedError(
        "Too many files are being sent at once; send this one again shortly.",
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(code),
                message=ErrorReasonMessage(
                    "The chat is taking other files; try again in a few seconds."
                ),
            )
        ],
        retry_after_seconds=RetryAfterSeconds(BUSY_RETRY_SECONDS),
    )
