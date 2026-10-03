"""What the cabinet reports: Web Vitals of its pages and the tunnel's steps."""

from typing import Annotated, Literal

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.analytics import (
    DeviceClass,
    TelemetryEventKind,
    TunnelStepAction,
    TunnelStepKey,
    WebVitalName,
)
from app.schemas.typings.analytics.constrained_integers import (
    TelemetryReportCount,
    WebVitalValue,
)
from app.schemas.typings.analytics.constrained_strings import CabinetRoutePattern
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

MAX_TELEMETRY_BATCH: int = 50


class WebVitalReport(ImmutableDTO):
    """
    One Core Web Vital of a page view: LCP and INP in whole milliseconds,
    CLS in ten-thousandths (0.1 is 1000); the page as its route template.
    """

    kind: Literal[TelemetryEventKind.WEB_VITAL]
    metric: WebVitalName
    value: WebVitalValue
    route: CabinetRoutePattern
    device_class: DeviceClass


class TunnelStepReport(ImmutableDTO):
    """
    The owner entered a screen of the setup tunnel, or went on from it;
    the business once it exists (the first two screens come before it).
    """

    kind: Literal[TelemetryEventKind.TUNNEL_STEP]
    step: TunnelStepKey
    action: TunnelStepAction
    business_id: BusinessId | None = None


type TelemetryReport = Annotated[
    WebVitalReport | TunnelStepReport, Field(discriminator="kind")
]


class TelemetryBatchRequest(ImmutableDTO):
    """HTTP body of POST /v1/telemetry/events: up to 50 reports at once."""

    events: list[TelemetryReport] = Field(min_length=1, max_length=MAX_TELEMETRY_BATCH)


class TelemetryBatchCommand(ImmutableDTO):
    """A signed-in person's batch of cabinet reports."""

    user_id: UserId
    events: list[TelemetryReport]


class TelemetryBatchReceipt(ImmutableDTO):
    """How many Web Vitals and tunnel steps of the batch were kept."""

    web_vitals: TelemetryReportCount
    tunnel_steps: TelemetryReportCount
