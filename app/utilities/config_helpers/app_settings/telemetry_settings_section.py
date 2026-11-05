"""
METRICS_TOKEN, WORKER_METRICS_PORT, PROMETHEUS_MULTIPROC_DIR and OTEL_*:
Prometheus metrics and OpenTelemetry traces (both off unless configured).
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.telemetry_settings import (
    DEFAULT_OTEL_TRACES_SAMPLE_RATE,
    TelemetrySettings,
)
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.observability.constrained_integers import MetricsPort
from app.schemas.typings.observability.constrained_strings import OtelServiceName
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from app.schemas.typings.platform.strings import LocalDirectoryPath, PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_setting,
    optional_text,
    parse_setting,
    read_float,
)


class TelemetrySettingsSection(TypedDict):
    """The `AppSettings` field of metrics and traces."""

    telemetry: TelemetrySettings


def read_telemetry_settings(
    environment_variables: Mapping[str, str],
) -> TelemetrySettingsSection:
    return TelemetrySettingsSection(
        telemetry=TelemetrySettings(
            metrics_token=optional_text(
                environment_variables, "METRICS_TOKEN", PlatformSecret
            ),
            worker_metrics_port=optional_setting(
                environment_variables,
                "WORKER_METRICS_PORT",
                lambda raw: MetricsPort(int(raw)),
            ),
            # prometheus_client reads it itself; the API reads it to merge
            # the series of its processes.
            prometheus_multiproc_directory=optional_text(
                environment_variables, "PROMETHEUS_MULTIPROC_DIR", LocalDirectoryPath
            ),
            otlp_endpoint=optional_setting(
                environment_variables, "OTEL_EXPORTER_OTLP_ENDPOINT", PublicBaseUrl
            ),
            otlp_headers=optional_text(
                environment_variables, "OTEL_EXPORTER_OTLP_HEADERS", PlatformSecret
            ),
            otel_service_name=optional_setting(
                environment_variables, "OTEL_SERVICE_NAME", OtelServiceName
            ),
            otel_traces_sample_rate=parse_setting(
                "OTEL_TRACES_SAMPLE_RATE",
                read_float(
                    environment_variables,
                    "OTEL_TRACES_SAMPLE_RATE",
                    DEFAULT_OTEL_TRACES_SAMPLE_RATE,
                ),
                TraceSampleRate,
            ),
        )
    )
