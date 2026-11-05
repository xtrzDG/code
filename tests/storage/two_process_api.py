"""
One API process of the two-process test:

    python -m tests.storage.two_process_api <port> <model call log>

The real application on the test database (settings from the environment,
DATABASE_URL among them), served by uvicorn. Only the language model is a
stand-in: it answers every call after a pause and appends when the call
started and ended to the log file, so the test can see whether two turns of
one customer ever overlapped across the processes.
"""

import os
import sys
import time
from pathlib import Path

import uvicorn

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.containers.app import AppContainer
from app.main import build_application
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.conversations.strings import MessageText
from tests.e2e.workshop_container import replace_provider

MODEL_CALL_SECONDS: float = 0.4
REPLY: str = "Спасибо! Сейчас уточню и отвечу."


class LoggingSlowModel(ScriptedLlmAdapter):
    """Answers after a pause; one log line per call: pid, start, end."""

    def __init__(self, call_log: Path) -> None:
        super().__init__(lambda _request: ScriptedLlmTurn(text=MessageText(REPLY)))
        self._call_log: Path = call_log

    def complete(self, request: LlmRequest) -> LlmResponse:
        started = time.time()
        time.sleep(MODEL_CALL_SECONDS)
        response = super().complete(request)
        line = f"{os.getpid()} {started:.6f} {time.time():.6f}\n"
        # One short append per call: atomic between processes.
        with self._call_log.open("a", encoding="utf-8") as log:
            log.write(line)
        return response


def main() -> None:
    port, call_log = int(sys.argv[1]), Path(sys.argv[2])
    container = AppContainer()
    replace_provider(container.adapters.routing_llm_adapter, LoggingSlowModel(call_log))
    uvicorn.run(
        build_application(container),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
