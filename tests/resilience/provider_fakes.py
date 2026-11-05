"""
Providers as the bulkhead tests play them: Meta's Graph API that hangs,
fails or answers on the test's word, a Bot API that always answers, and
the states each circuit breaker took.
"""

import json
import threading
from enum import StrEnum

import httpx

from app.schemas.constants.resilience import CircuitState
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.observability.metrics.null_service_metrics import (
    NullServiceMetrics,
)

# A provider that hangs holds a thread until its read timeout (10 s).
HANG_SECONDS: float = 10.0
# Upper bound of every wait for the worker's threads; a passing test
# never waits long.
WAIT_SECONDS: float = 10.0


class MetaMode(StrEnum):
    HANG = "hang"
    FAIL = "fail"
    ANSWER = "answer"


class BrownOutMeta:
    """
    Meta's Graph API as the test plays it: sends hang (until let go, at most
    HANG_SECONDS, then a read timeout), fail at once (a read timeout) or
    answer. Counts the sends in flight (the most at once), the ones that
    hung and the ones it accepted.
    """

    def __init__(self, mode: MetaMode) -> None:
        self.mode: MetaMode = mode
        self.attempts: list[str] = []
        self.hung: list[str] = []
        self.accepted: list[str] = []
        self.most_in_flight: int = 0
        self._in_flight: int = 0
        self._hanging: int = 0
        self._changed = threading.Condition()
        self._let_go = threading.Event()

    def handle(self, request: httpx.Request) -> httpx.Response:
        recipient: str = str(json.loads(request.content)["to"])
        with self._changed:
            self.attempts.append(recipient)
            self._in_flight += 1
            self.most_in_flight = max(self.most_in_flight, self._in_flight)
            mode: MetaMode = self.mode
            if mode is MetaMode.HANG:
                self.hung.append(recipient)
                self._hanging += 1
            self._changed.notify_all()

        try:
            return self._answer(request, recipient, mode)
        finally:
            with self._changed:
                self._in_flight -= 1
                self._changed.notify_all()

    def _answer(
        self, request: httpx.Request, recipient: str, mode: MetaMode
    ) -> httpx.Response:
        if mode is MetaMode.HANG:
            self._let_go.wait(HANG_SECONDS)

        if mode is not MetaMode.ANSWER:
            raise httpx.ReadTimeout("Meta did not answer in time.", request=request)

        with self._changed:
            self.accepted.append(recipient)
            message_id: str = f"wamid.{len(self.accepted)}"

        return httpx.Response(200, json={"messages": [{"id": message_id}]})

    def wait_for_hanging(self, count: int) -> bool:
        with self._changed:
            return self._changed.wait_for(
                lambda: self._hanging >= count, timeout=WAIT_SECONDS
            )

    def answer_from_now_on(self) -> None:
        """Meta recovers: the hanging sends time out, new ones are answered."""

        with self._changed:
            self.mode = MetaMode.ANSWER
        self._let_go.set()


class AnsweringTelegram:
    """The Bot API: every call is answered; the test waits for sends."""

    def __init__(self) -> None:
        self.sent_with: list[str] = []
        self._changed = threading.Condition()

    def handle(self, request: httpx.Request) -> httpx.Response:
        bot_token: str = request.url.path.split("/")[1].removeprefix("bot")
        with self._changed:
            self.sent_with.append(bot_token)
            message_id: int = len(self.sent_with)
            self._changed.notify_all()

        return httpx.Response(
            200, json={"ok": True, "result": {"message_id": message_id}}
        )

    def wait_for_sends(self, count: int, timeout: float) -> bool:
        with self._changed:
            return self._changed.wait_for(
                lambda: len(self.sent_with) >= count, timeout=timeout
            )


class CircuitStates(NullServiceMetrics):
    """Every state a circuit took, in order (the breaker's /metrics gauge)."""

    def __init__(self) -> None:
        self.changes: list[tuple[CircuitName, CircuitState]] = []

    def set_circuit_state(self, circuit: CircuitName, state: CircuitState) -> None:
        self.changes.append((circuit, state))

    def of(self, circuit: CircuitName) -> list[CircuitState]:
        return [state for name, state in self.changes if name == circuit]
