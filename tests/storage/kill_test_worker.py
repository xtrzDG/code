"""
One customer worker of the kill test:

    python -m tests.storage.kill_test_worker <directory> <lease seconds>

The real worker on the test database (settings from the environment:
DATABASE_URL, WORKER_LANES, ...; JSON logs on stderr) with a job lease of
<lease seconds>, a stand-in model and a stand-in Telegram. The first model
call of all the workers hangs until the test kills its process (SIGKILL);
it leaves the process's pid in `<directory>/first-call.pid` first. Every
other call answers at once and appends "pid start end" to
`<directory>/model-calls.log`. Every message sent to Telegram is appended
to `<directory>/telegram-sends.log` as a JSON line.
"""

import json
import os
import sys
import time
from pathlib import Path

import httpx

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.containers.app import AppContainer
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_integers import JobLeaseSeconds
from app.utilities.observability.logging_setup import configure_logging
from app.worker_main import main as run_worker
from tests.e2e.edge_fakes import answer_telegram
from tests.e2e.workshop_container import replace_provider
from tests.storage.two_process_api import REPLY

FIRST_CALL_MARKER: str = "first-call.pid"
MODEL_CALL_LOG: str = "model-calls.log"
TELEGRAM_SENDS: str = "telegram-sends.log"
HANG_STEP_SECONDS: float = 60.0


class HangsOnTheFirstCall(ScriptedLlmAdapter):
    """The first call of all the workers hangs; the others answer at once."""

    def __init__(self, directory: Path) -> None:
        super().__init__(lambda _request: ScriptedLlmTurn(text=MessageText(REPLY)))
        self._directory: Path = directory

    def complete(self, request: LlmRequest) -> LlmResponse:
        if self._is_first_call():
            while True:  # mid-turn until the test kills this process
                time.sleep(HANG_STEP_SECONDS)

        started = time.time()
        response = super().complete(request)
        with (self._directory / MODEL_CALL_LOG).open("a", encoding="utf-8") as log:
            log.write(f"{os.getpid()} {started:.6f} {time.time():.6f}\n")
        return response

    def _is_first_call(self) -> bool:
        """
        Claim the first call: the marker is linked in place whole (pid and
        all), and a link never replaces a file another process linked first.
        """

        own = self._directory / f"call-{os.getpid()}-{time.monotonic_ns()}.pid"
        own.write_text(str(os.getpid()), encoding="utf-8")
        try:
            os.link(own, self._directory / FIRST_CALL_MARKER)
        except FileExistsError:
            return False
        finally:
            own.unlink()

        return True


def stand_in_telegram(directory: Path) -> httpx.MockTransport:
    """Telegram's answers; the messages sent are appended to the log."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sendMessage"):
            body = json.loads(request.content)
            line = json.dumps({"pid": os.getpid(), "text": body["text"]})
            with (directory / TELEGRAM_SENDS).open("a", encoding="utf-8") as log:
                log.write(line + "\n")
        return httpx.Response(200, json=answer_telegram(request))

    return httpx.MockTransport(handle)


def main() -> None:
    directory, lease_seconds = Path(sys.argv[1]), JobLeaseSeconds(int(sys.argv[2]))
    container = AppContainer()
    configure_logging(container.config.app_settings().log_format)
    replace_provider(
        container.adapters.routing_llm_adapter, HangsOnTheFirstCall(directory)
    )
    replace_provider(
        container.clients.telegram_bot_client,
        TelegramBotClient(transport=stand_in_telegram(directory)),
    )
    replace_provider(
        container.gateways.background_worker,
        container.gateways.background_worker(lease_seconds=lease_seconds),
    )
    raise SystemExit(run_worker(container))


if __name__ == "__main__":
    main()
