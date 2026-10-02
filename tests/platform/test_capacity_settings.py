"""Request threads, database connections, log format, release and tracing settings."""

import anyio.to_thread
import pytest
from fastapi.testclient import TestClient

from app.containers.app import AppContainer
from app.main import build_application
from app.schemas.constants.observability import LogFormat
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.workshop_container import replace_provider

PRODUCTION: dict[str, str] = {"APP_ENV": "production", "ENCRYPTION_KEY": "x" * 40}


def test_the_database_pool_follows_the_request_threads_unless_set() -> None:
    default = assemble_app_settings({})
    fewer_threads = assemble_app_settings({"THREADPOOL_SIZE": "32"})
    own_pool = assemble_app_settings({"THREADPOOL_SIZE": "32", "DB_POOL_SIZE": "20"})

    assert (int(default.threadpool_size), int(default.db_pool_size)) == (64, 64)
    assert (int(fewer_threads.threadpool_size), int(fewer_threads.db_pool_size)) == (
        32,
        32,
    )
    assert int(own_pool.db_pool_size) == 20


@pytest.mark.parametrize(
    "environment",
    [
        {"THREADPOOL_SIZE": "0"},
        {"DB_POOL_SIZE": "100000"},
        {"SENTRY_TRACES_SAMPLE_RATE": "1.5"},
        {"LOG_FORMAT": "xml"},
        {"LLM_CALL_TIMEOUT_SECONDS": "0"},
        {"APP_RELEASE": "not a release!"},
    ],
)
def test_out_of_range_values_stop_the_start(environment: dict[str, str]) -> None:
    with pytest.raises(ValidationFailedError, match=next(iter(environment))):
        assemble_app_settings(environment)


def test_logs_are_json_in_production_and_text_elsewhere() -> None:
    assert assemble_app_settings({}).log_format is LogFormat.TEXT
    assert assemble_app_settings(PRODUCTION).log_format is LogFormat.JSON
    assert (
        assemble_app_settings({**PRODUCTION, "LOG_FORMAT": "TEXT"}).log_format
        is LogFormat.TEXT
    )


def test_the_release_is_named_explicitly_or_by_render() -> None:
    render = assemble_app_settings({"RENDER_GIT_COMMIT": "4718714c0f2e"})
    both = assemble_app_settings(
        {"RENDER_GIT_COMMIT": "4718714c0f2e", "APP_RELEASE": "2026.10.1"}
    )

    assert assemble_app_settings({}).release_version is None
    assert render.release_version == ReleaseVersion("4718714c0f2e")
    assert both.release_version == ReleaseVersion("2026.10.1")
    assert assemble_app_settings({}).sentry_traces_sample_rate == TraceSampleRate(0.05)


def test_startup_sizes_the_request_thread_pool() -> None:
    container = AppContainer()
    replace_provider(
        container.config.app_settings,
        assemble_app_settings({"THREADPOOL_SIZE": "48", "EMBEDDED_WORKER": "false"}),
    )
    application = build_application(container)

    @application.get("/thread-limit")
    async def thread_limit() -> dict[str, int]:
        limiter = anyio.to_thread.current_default_thread_limiter()
        return {"total_tokens": int(limiter.total_tokens)}

    with TestClient(application) as client:
        response = client.get("/thread-limit")

    assert response.json() == {"total_tokens": 48}
