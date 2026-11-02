"""
Doubles of the failure signal tests: a signal counter that records each
count, an error reporter that drops reports, and an error raised inside a
module of the object storage client.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.platform_alerts import SignalTally
from app.schemas.typings.monitoring.constrained_integers import SignalEventCount

OBJECT_STORAGE_MODULE: str = "app.clients.object_storage.s3_object_storage_client"
RAISING_SOURCE: str = (
    "def upload():\n    raise TimeoutError('the bucket did not answer')\n"
)


class CountedSignals:
    """Every signal counted, in order."""

    def __init__(self) -> None:
        self.calls: list[PlatformSignal] = []

    def count(self, signal: PlatformSignal) -> None:
        self.calls.append(signal)

    def read(self, signal: PlatformSignal, now: Microseconds) -> SignalTally:
        del now
        return SignalTally(
            signal=signal,
            current=SignalEventCount(self.of(signal)),
            previous=SignalEventCount(0),
        )

    def of(self, signal: PlatformSignal) -> int:
        return self.calls.count(signal)


class NoErrorReports:
    """An error reporter that drops every report."""

    def capture_exception(self, error: BaseException) -> None:
        del error


def raise_in_object_storage() -> TimeoutError:
    """An error whose innermost frame is in the object storage client."""

    namespace: dict[str, object] = {"__name__": OBJECT_STORAGE_MODULE}
    exec(compile(RAISING_SOURCE, "<object storage>", "exec"), namespace)  # noqa: S102  # nosec B102 - a fixed test source
    upload = namespace["upload"]
    assert callable(upload)
    try:
        upload()
    except TimeoutError as error:
        return error
    raise AssertionError("upload() did not raise")
