"""CORS_ALLOWED_ORIGINS, the background worker and the recordings directory."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.booleans import IsEmbeddedWorkerEnabled
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.schemas.typings.platform.strings import LocalDirectoryPath
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    FALSE_VALUES,
    TRUE_VALUES,
    read_integer,
    read_raw_list,
    read_text,
)

# Call recordings kept on this server (development or a single server);
# recordings of ElevenLabs calls stay in ElevenLabs storage.
DEFAULT_RECORDINGS_DIRECTORY: str = "var/recordings"
# EMBEDDED_WORKER: "auto" decides by the environment (see read_embedded_worker).
EMBEDDED_WORKER_AUTO: str = "auto"


class RuntimeSettingsSection(TypedDict):
    """The `AppSettings` fields of how the processes run."""

    cors_allowed_origins: list[PublicBaseUrl]
    worker_poll_seconds: WorkerPollSeconds
    is_embedded_worker_enabled: IsEmbeddedWorkerEnabled
    recordings_directory: LocalDirectoryPath


def read_runtime_settings(
    environment_variables: Mapping[str, str],
    environment: DeploymentEnvironment,
    has_database: bool,
) -> RuntimeSettingsSection:
    return RuntimeSettingsSection(
        cors_allowed_origins=[
            PublicBaseUrl(origin)
            for origin in read_raw_list(environment_variables, "CORS_ALLOWED_ORIGINS")
        ],
        worker_poll_seconds=WorkerPollSeconds(
            read_integer(environment_variables, "WORKER_POLL_SECONDS", 15)
        ),
        is_embedded_worker_enabled=IsEmbeddedWorkerEnabled(
            read_embedded_worker(
                environment_variables,
                environment=environment,
                has_database=has_database,
            )
        ),
        recordings_directory=LocalDirectoryPath(
            read_text(
                environment_variables,
                "RECORDINGS_DIRECTORY",
                DEFAULT_RECORDINGS_DIRECTORY,
            )
        ),
    )


def read_embedded_worker(
    environment_variables: Mapping[str, str],
    environment: DeploymentEnvironment,
    has_database: bool,
) -> bool:
    """
    EMBEDDED_WORKER: whether the API runs the background worker (periodic
    jobs and the job queue: autotests, reminders) in a thread of its own
    process.

    - `auto` (default): on in development without DATABASE_URL. In-memory
      storage lives inside one process, so a separate worker would never
      see the API's data: autotests would stay "running" and reminders
      would never go out.
    - `true`: on (e.g. development against a local Postgres without the
      separate worker). Refused in production: the worker assumes it is
      the only one, and a production API may run in several processes or
      instances next to `workshop worker`, so jobs would run twice.
    - `false`: off; run `python -m app.worker_main` (`workshop worker`).

    Raises:
        ValidationFailedError: an unknown value, or `true` in production.
    """

    raw_value: str = environment_variables.get("EMBEDDED_WORKER", "").strip().lower()
    if raw_value in {"", EMBEDDED_WORKER_AUTO}:
        return environment is DeploymentEnvironment.DEVELOPMENT and not has_database

    if raw_value in FALSE_VALUES:
        return False

    if raw_value not in TRUE_VALUES:
        raise ValidationFailedError(
            f"EMBEDDED_WORKER must be auto, true or false, got {raw_value!r}."
        )

    if environment is DeploymentEnvironment.PRODUCTION:
        raise ValidationFailedError(
            "EMBEDDED_WORKER cannot be true in production: run the background "
            "worker as its own single process (`workshop worker`), or jobs run "
            "once per API process."
        )

    return True
