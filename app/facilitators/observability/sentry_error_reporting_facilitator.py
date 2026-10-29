import logging
from collections.abc import Callable

import sentry_sdk
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.contracts.observability import (
    ClientErrorReportingFacilitatorContract,
    ErrorReportingFacilitatorContract,
)
from app.facilitators.observability.sentry_event_scrubbing import (
    scrub_event,
    scrub_transaction,
)
from app.facilitators.observability.sentry_trace_sampling import build_trace_sampler
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.dto.widget_errors import WidgetErrorReport
from app.schemas.typings.platform.constrained_floats import TraceSampleRate
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.observability.log_context import (
    log_context_of_error,
    restored_log_context,
)

__all__ = ["SentryErrorReportingFacilitator", "scrub_event"]

type SentryInit = Callable[..., object]

LOGGER: logging.Logger = logging.getLogger(__name__)
NO_TRACES: TraceSampleRate = TraceSampleRate(0.0)
WIDGET_LOGGER: logging.Logger = logging.getLogger("app.widget")


class SentryErrorReportingFacilitator(
    ErrorReportingFacilitatorContract,
    ClientErrorReportingFacilitatorContract,
):
    """
    Reports unexpected errors, and the website widget's errors, to Sentry
    without personal data: request bodies, users and breadcrumbs are
    removed before sending (conversations contain customers' personal data,
    which must stay in the EU processing chain described by the concept).

    Every report names the deployed build (`release`) and carries the log
    context as tags (request, business, conversation, channel, job), so it
    can be traced to one request or job. A share of API requests
    (SENTRY_TRACES_SAMPLE_RATE; widget polls a hundredth of it,
    `sentry_trace_sampling`) is traced, by route template, without URLs or
    bodies; its calls to providers over httpx are spans of the trace (the
    host and a path template, `scrub_span`), and no trace header goes to a
    provider (`trace_propagation_targets` is empty). Integrations are
    listed explicitly: none of the SDK's automatic ones (model clients)
    records prompts or URLs. Without a DSN every error goes to the log
    instead.
    """

    def __init__(
        self,
        dsn: PlatformSecret | None,
        environment: DeploymentEnvironment,
        release: ReleaseVersion | None = None,
        traces_sample_rate: TraceSampleRate = NO_TRACES,
        sentry_init: SentryInit = sentry_sdk.init,
    ) -> None:
        self._is_enabled: bool = dsn is not None
        if dsn is None:
            return

        integrations: list[Integration] = [
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
            HttpxIntegration(),
        ]
        sentry_init(
            dsn=str(dsn),
            environment=str(environment),
            release=None if release is None else str(release),
            send_default_pii=False,
            max_request_body_size="never",
            traces_sample_rate=float(traces_sample_rate),
            traces_sampler=build_trace_sampler(traces_sample_rate),
            before_send=scrub_event,
            before_send_transaction=scrub_transaction,
            auto_enabling_integrations=False,
            integrations=integrations,
            trace_propagation_targets=[],
        )

    @property
    def is_enabled(self) -> bool:
        """True when reports go to Sentry (SENTRY_DSN is set)."""

        return self._is_enabled

    def capture_exception(self, error: BaseException) -> None:
        # The context the error was raised in: the request and business of
        # an HTTP 500, the job of a worker failure.
        with restored_log_context(log_context_of_error(error)) as context:
            if not self._is_enabled:
                LOGGER.error("Unexpected error", exc_info=error)
                return

            try:
                sentry_sdk.capture_exception(error, tags=context.as_fields())
            except Exception:  # noqa: BLE001 - reporting must never fail the caller
                LOGGER.exception("Sentry capture failed")

    def capture_widget_error(self, report: WidgetErrorReport) -> None:
        tags: dict[str, str] = {
            name: str(value)
            for name, value in report.model_dump(mode="json").items()
            if value is not None
        }
        WIDGET_LOGGER.warning(
            "Website widget error: %s",
            " ".join(f"{name}={value}" for name, value in tags.items()),
        )
        if not self._is_enabled:
            return

        try:
            sentry_sdk.capture_message(
                f"Website widget {report.kind.value} in {report.phase.value}",
                level="warning",
                tags={"source": "widget", **tags},
                fingerprint=[
                    "widget",
                    report.kind.value,
                    report.phase.value,
                    tags.get("error_name", ""),
                    tags.get("line", ""),
                ],
            )
        except Exception:  # noqa: BLE001 - reporting must never fail the caller
            LOGGER.exception("Sentry capture failed")
