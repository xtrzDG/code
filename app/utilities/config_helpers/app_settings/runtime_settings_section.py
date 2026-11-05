"""
APP_ENV, CORS_ALLOWED_ORIGINS, the request threads and database
connections, the background worker, the development demo data and the
recordings directory.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.jobs import JobLane
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.booleans import (
    IsDemoDataSeedingEnabled,
    IsEmbeddedWorkerEnabled,
)
from app.schemas.typings.platform.constrained_integers import (
    DatabasePoolSize,
    ThreadPoolSize,
    WorkerLaneConcurrency,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.strings import LocalDirectoryPath
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    FALSE_VALUES,
    TRUE_VALUES,
    parse_setting,
    read_boolean,
    read_integer,
    read_raw_list,
    read_text,
    read_typed_integer,
)
from app.utilities.config_helpers.app_settings.worker_lane_settings import (
    read_worker_lane_concurrency,
    read_worker_lanes,
)

# Call recordings kept on this server (development or a single server);
# recordings of ElevenLabs calls stay in ElevenLabs storage.
DEFAULT_RECORDINGS_DIRECTORY: str = "var/recordings"
# EMBEDDED_WORKER: "auto" decides by the environment (see read_embedded_worker).
EMBEDDED_WORKER_AUTO: str = "auto"
# Request handlers that may run at once in threads (AnyIO's default is 40).
DEFAULT_THREADPOOL_SIZE: int = 64
# Render sets RENDER=true on every service: there a missing APP_ENV is a
# deployment mistake, never a development machine.
RENDER_MARKER_VARIABLE: str = "RENDER"
# A browser sends the cabinet's cookies only to listed origins; "*" would
# list every site.
ANY_ORIGIN: str = "*"


class RuntimeSettingsSection(TypedDict):
    """The `AppSettings` fields of how the processes run."""

    cors_allowed_origins: list[PublicBaseUrl]
    threadpool_size: ThreadPoolSize
    db_pool_size: DatabasePoolSize
    worker_poll_seconds: WorkerPollSeconds
    worker_lane_concurrency: dict[JobLane, WorkerLaneConcurrency]
    worker_lanes: tuple[JobLane, ...]
    is_embedded_worker_enabled: IsEmbeddedWorkerEnabled
    is_demo_data_seeding_enabled: IsDemoDataSeedingEnabled
    recordings_directory: LocalDirectoryPath


def read_deployment_environment(
    environment_variables: Mapping[str, str],
) -> DeploymentEnvironment:
    """
    APP_ENV: development (the default on a developer's machine), test or
    production.

    Raises:
        ValidationFailedError: another value (a typo such as "prod" must not
            start a process with development's leniency), or APP_ENV unset
            where Render runs the process (RENDER is set).
    """

    raw_value: str = environment_variables.get("APP_ENV", "").strip().lower()
    if raw_value == "":
        if environment_variables.get(RENDER_MARKER_VARIABLE, "").strip() != "":
            raise ValidationFailedError(
                "APP_ENV is not set, and this process runs on Render (RENDER is "
                "set): set APP_ENV=production (render.yaml sets it for every "
                "backend service) or development explicitly."
            )

        return DeploymentEnvironment.DEVELOPMENT

    try:
        return DeploymentEnvironment(raw_value)
    except ValueError as error:
        raise ValidationFailedError(
            "APP_ENV must be one of "
            + ", ".join(environment.value for environment in DeploymentEnvironment)
            + f", got {raw_value!r}."
        ) from error


def read_cors_allowed_origins(
    environment_variables: Mapping[str, str],
) -> list[PublicBaseUrl]:
    """
    CORS_ALLOWED_ORIGINS: the cabinet's origins (comma-separated).

    Raises:
        ValidationFailedError: "*" or a value that is not an http(s) origin.
    """

    origins: list[str] = read_raw_list(environment_variables, "CORS_ALLOWED_ORIGINS")
    if ANY_ORIGIN in origins:
        raise ValidationFailedError(
            'CORS_ALLOWED_ORIGINS cannot be "*": the cabinet signs in with '
            "cookies, so list its origins (https://app.example.com)."
        )

    return [
        parse_setting("CORS_ALLOWED_ORIGINS", origin, PublicBaseUrl)
        for origin in origins
    ]


def read_runtime_settings(
    environment_variables: Mapping[str, str],
    environment: DeploymentEnvironment,
    has_database: bool,
) -> RuntimeSettingsSection:
    threadpool_size: int = read_integer(
        environment_variables, "THREADPOOL_SIZE", DEFAULT_THREADPOOL_SIZE
    )
    return RuntimeSettingsSection(
        cors_allowed_origins=read_cors_allowed_origins(environment_variables),
        threadpool_size=parse_setting(
            "THREADPOOL_SIZE", threadpool_size, ThreadPoolSize
        ),
        db_pool_size=parse_setting(
            "DB_POOL_SIZE",
            read_integer(
                environment_variables,
                "DB_POOL_SIZE",
                default_db_pool_size(threadpool_size),
            ),
            DatabasePoolSize,
        ),
        worker_poll_seconds=read_typed_integer(
            environment_variables, "WORKER_POLL_SECONDS", 15, WorkerPollSeconds
        ),
        worker_lane_concurrency=read_worker_lane_concurrency(environment_variables),
        worker_lanes=read_worker_lanes(environment_variables),
        is_embedded_worker_enabled=IsEmbeddedWorkerEnabled(
            read_embedded_worker(
                environment_variables,
                environment=environment,
                has_database=has_database,
            )
        ),
        is_demo_data_seeding_enabled=IsDemoDataSeedingEnabled(
            read_demo_data_seeding(environment_variables, environment)
        ),
        recordings_directory=LocalDirectoryPath(
            read_text(
                environment_variables,
                "RECORDINGS_DIRECTORY",
                DEFAULT_RECORDINGS_DIRECTORY,
            )
        ),
    )


def default_db_pool_size(threadpool_size: int) -> int:
    """
    DB_POOL_SIZE when unset: half the request threads (at least one). A
    thread holds a connection only for its statements, never while it waits
    for the model or another service, so the threads beyond the pool wait a
    moment for a connection instead of the database running out of them.
    """

    return max(1, (threadpool_size + 1) // 2)


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
      separate worker). Refused in production: workers may run side by side
      (leased claims), but there the API serves requests and the workers
      (`workshop worker`, as many as needed) run the model-heavy jobs.
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
            "EMBEDDED_WORKER cannot be true in production: run background "
            "workers as their own service (`workshop worker`), so autotests "
            "and other long jobs never slow down the API."
        )

    return True


def read_demo_data_seeding(
    environment_variables: Mapping[str, str],
    environment: DeploymentEnvironment,
) -> bool:
    """
    SEED_DEMO_DATA (default false): the API fills the instance with demo
    businesses at startup, once (a Tbilisi restaurant and a Berlin salon
    with a demo owner, a staff member and a month of activity). Refused in
    production: the demo accounts would be real accounts there.

    Raises:
        ValidationFailedError: not a boolean, or true in production.
    """

    is_enabled: bool = read_boolean(environment_variables, "SEED_DEMO_DATA", False)
    if is_enabled and environment is DeploymentEnvironment.PRODUCTION:
        raise ValidationFailedError(
            "SEED_DEMO_DATA cannot be enabled in production: it creates demo "
            "accounts and businesses. Use it in development only."
        )

    return is_enabled
