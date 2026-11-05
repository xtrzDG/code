"""
One background worker process of the multi-process tests:

    python -m tests.storage.two_process_worker <model call log>

The real worker on the test database (settings from the environment,
DATABASE_URL among them; logs as JSON lines on stderr), with the logging
stand-in model of `two_process_api`: it answers every call after a pause
and logs when the call started and ended. SIGTERM stops it.
"""

import sys
from pathlib import Path

from app.containers.app import AppContainer
from app.utilities.observability.logging_setup import configure_logging
from app.worker_main import main as run_worker
from tests.e2e.workshop_container import replace_provider
from tests.storage.two_process_api import LoggingSlowModel


def main() -> None:
    call_log = Path(sys.argv[1])
    container = AppContainer()
    configure_logging(container.config.app_settings().log_format)
    replace_provider(container.adapters.routing_llm_adapter, LoggingSlowModel(call_log))
    raise SystemExit(run_worker(container))


if __name__ == "__main__":
    main()
