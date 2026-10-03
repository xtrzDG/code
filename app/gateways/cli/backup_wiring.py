"""
What `workshop backup` and `workshop restore-check` share: the settings,
the bucket client, Sentry (errors and Crons check-ins) and a temporary
work directory for the dump and the archive.
"""

import tempfile
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from typed_time_provider import Microseconds, WallClock

from app.clients.object_storage.s3_backup_bucket_client import S3BackupBucketClient
from app.contracts.observability import JobMonitorFacilitatorContract
from app.facilitators.observability.job_monitor_factory import (
    build_job_monitor_facilitator,
)
from app.facilitators.observability.sentry_error_reporting_facilitator import (
    SentryErrorReportingFacilitator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.dto.object_storage import ObjectStorageConnection
from app.schemas.dto.observability import JobCheckIn
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import LocalDirectoryPath
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_NOT_CONFIGURED: int = 2


def load_settings(
    environment_variables: Mapping[str, str],
    error_stream: TextIO,
) -> AppSettings | None:
    try:
        return assemble_app_settings(environment_variables)
    except (ApplicationError, ValueError) as error:
        # Typed primitives and enums raise ValueError subclasses.
        print(f"Invalid settings: {error}", file=error_stream)
        return None


def build_bucket(connection: ObjectStorageConnection) -> S3BackupBucketClient:
    """The bucket client; presigned URLs use the system clock (S3's time)."""

    return S3BackupBucketClient(
        connection=connection,
        wall_clock=WallClock(preferred_time_unit_type=Microseconds),
    )


@contextmanager
def work_directory(parent: str | None) -> Generator[LocalDirectoryPath]:
    """A private temporary directory, deleted with everything in it."""

    if parent is not None:
        Path(parent).mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="workshop-backup-", dir=parent) as path:
        yield LocalDirectoryPath(path)


class MonitoredRun:
    """
    One run of a scheduled command, reported to Sentry when SENTRY_DSN is
    set: a Crons check-in when it starts and ends (a run that never comes
    shows up as missed) and the error that failed it.
    """

    def __init__(
        self,
        settings: AppSettings,
        job_name: JobName,
        interval: JobIntervalSeconds,
    ) -> None:
        self._error_reporter = SentryErrorReportingFacilitator(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            release=settings.release_version,
        )
        self._monitor: JobMonitorFacilitatorContract = build_job_monitor_facilitator(
            self._error_reporter
        )
        self._job_name: JobName = job_name
        self._interval: JobIntervalSeconds = interval

    def run[Result](
        self,
        work: Callable[[], Result],
        is_success: Callable[[Result], bool],
    ) -> Result:
        """Run the work; an exception is reported and raised again."""

        check_in: JobCheckIn = self._monitor.job_started(self._job_name, self._interval)
        try:
            result: Result = work()
        except Exception as error:
            self._error_reporter.capture_exception(error)
            self._monitor.job_finished(check_in, PeriodicJobOutcome.FAILED)
            raise

        self._monitor.job_finished(
            check_in,
            PeriodicJobOutcome.SUCCEEDED
            if is_success(result)
            else PeriodicJobOutcome.FAILED,
        )
        return result

    def report_failure(self, error: Exception) -> None:
        self._error_reporter.capture_exception(error)
