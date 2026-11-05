"""
The failure signals a process counts for the platform health alerts
(LOG-04): which store an error comes from, the per-minute limit of each
signal, slow requests, and the places that count them (the HTTP error
handlers, the job failure reporter).
"""

from collections.abc import Callable
from types import SimpleNamespace

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.failure_signals import (
    PER_MINUTE_LIMIT,
    FailureSignals,
    failure_signals_of,
)
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.worker.job_failure_reporter import JobFailureReporter
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    NotFoundError,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.observability.failure_kinds import (
    StoreFailureKind,
    store_failure_of,
)
from tests.platform_ops.failure_signal_doubles import (
    CountedSignals,
    NoErrorReports,
    raise_in_object_storage,
)


class Minutes:
    """A monotonic clock the test moves a minute at a time."""

    def __init__(self) -> None:
        self.seconds: float = 1_000.0

    def __call__(self) -> float:
        return self.seconds


def signals_of(
    counted: CountedSignals, clock: Callable[[], float] | None = None
) -> FailureSignals:
    return FailureSignals(
        counted, run_later=lambda work: work(), monotonic=clock or Minutes()
    )


def database_failure() -> ExternalServiceError:
    try:
        try:
            raise psycopg.OperationalError("connection refused")
        except psycopg.OperationalError as cause:
            raise ExternalServiceError("The database is unavailable.") from cause
    except ExternalServiceError as error:
        return error


def test_a_psycopg_error_or_one_caused_by_it_is_a_database_failure() -> None:
    assert store_failure_of(psycopg.OperationalError("down")) is (
        StoreFailureKind.DATABASE
    )
    assert store_failure_of(database_failure()) is StoreFailureKind.DATABASE


def test_an_error_raised_in_the_object_storage_client_is_its_failure() -> None:
    assert store_failure_of(raise_in_object_storage()) is (
        StoreFailureKind.OBJECT_STORAGE
    )


@pytest.mark.parametrize(
    "error",
    [ValueError("bad"), NotFoundError("gone"), ExternalServiceError("Meta is down")],
)
def test_other_errors_come_from_no_store(error: Exception) -> None:
    assert store_failure_of(error) is None


@pytest.mark.parametrize(
    ("database_error", "kind"),
    [
        (psycopg.errors.UniqueViolation("duplicate key"), None),
        (psycopg.errors.ForeignKeyViolation("no such row"), None),
        (psycopg.errors.UntranslatableCharacter("NUL in text"), None),
        (psycopg.errors.QueryCanceled("statement timeout"), StoreFailureKind.DATABASE),
        (psycopg.errors.SerializationFailure("retry"), StoreFailureKind.DATABASE),
        (psycopg.errors.UndefinedTable("no table"), StoreFailureKind.DATABASE),
    ],
)
def test_an_answer_about_the_data_is_no_store_failure(
    database_error: psycopg.Error, kind: StoreFailureKind | None
) -> None:
    try:
        try:
            raise database_error
        except psycopg.Error as cause:
            raise ExternalServiceError("The write failed.") from cause
    except ExternalServiceError as error:
        translated = error

    assert store_failure_of(database_error) is kind
    assert store_failure_of(translated) is kind


def test_a_cycle_of_causes_ends() -> None:
    first = RuntimeError("first")
    second = RuntimeError("second")
    first.__cause__ = second
    second.__cause__ = first

    assert store_failure_of(first) is None


def test_each_signal_counts_at_most_its_limit_a_minute() -> None:
    counted = CountedSignals()
    clock = Minutes()
    signals = signals_of(counted, clock)

    for _ in range(PER_MINUTE_LIMIT + 10):
        signals.count(PlatformSignal.WEBHOOK_REFUSED)
    signals.count(PlatformSignal.SLOW_API_REQUEST)
    clock.seconds += 60
    signals.count(PlatformSignal.WEBHOOK_REFUSED)

    assert counted.of(PlatformSignal.WEBHOOK_REFUSED) == PER_MINUTE_LIMIT + 1
    assert counted.of(PlatformSignal.SLOW_API_REQUEST) == 1


@pytest.mark.parametrize(("seconds", "times"), [(1.99, 0), (2.0, 1), (9.5, 1)])
def test_requests_of_two_seconds_or_longer_are_slow(seconds: float, times: int) -> None:
    counted = CountedSignals()

    signals_of(counted).count_if_slow(seconds)

    assert counted.of(PlatformSignal.SLOW_API_REQUEST) == times


def test_store_failures_count_by_their_store() -> None:
    counted = CountedSignals()
    signals = signals_of(counted)

    signals.count_store_failure(database_failure())
    signals.count_store_failure(raise_in_object_storage())
    signals.count_store_failure(ValueError("not a store"))

    assert counted.calls == [
        PlatformSignal.DATABASE_ERROR,
        PlatformSignal.OBJECT_STORAGE_ERROR,
    ]


def test_counts_are_written_by_a_background_thread() -> None:
    counted = CountedSignals()
    signals = FailureSignals(counted)

    signals.count(PlatformSignal.DATABASE_ERROR)
    signals.close()
    signals.close()

    assert counted.calls == [PlatformSignal.DATABASE_ERROR]


def test_an_application_holds_its_signals_in_its_state() -> None:
    signals = signals_of(CountedSignals())
    holder = SimpleNamespace(state=SimpleNamespace(failure_signals=signals))

    assert failure_signals_of(holder) is signals
    assert failure_signals_of(SimpleNamespace(state=SimpleNamespace())) is None
    assert failure_signals_of(object()) is None


def application_with(counted: CountedSignals) -> TestClient:
    application = FastAPI()
    application.state.failure_signals = signals_of(counted)
    install_error_handlers(application)

    @application.get("/v1/database")
    def database() -> None:
        raise database_failure()

    @application.get("/v1/missing")
    def missing() -> None:
        try:
            raise psycopg.OperationalError("no row")
        except psycopg.OperationalError as cause:
            raise NotFoundError("Nothing here.") from cause

    return TestClient(application)


def test_the_error_handlers_count_server_errors_of_a_store() -> None:
    counted = CountedSignals()
    client = application_with(counted)

    failed = client.get("/v1/database")
    refused = client.get("/v1/missing")

    assert failed.status_code == 502
    assert refused.status_code == 404
    assert counted.calls == [PlatformSignal.DATABASE_ERROR]


def test_the_job_failure_reporter_counts_store_failures() -> None:
    counted = CountedSignals()
    reporter = JobFailureReporter(NoErrorReports(), signals_of(counted))

    reporter.report(JobName("send_reminders"), database_failure())
    reporter.report(JobName("send_reminders"), ExternalServiceError("Meta is down"))

    assert counted.calls == [PlatformSignal.DATABASE_ERROR]


def test_a_reporter_without_signals_counts_nothing() -> None:
    JobFailureReporter(NoErrorReports()).report(
        JobName("send_reminders"), database_failure()
    )
