from typed_time_provider import Microseconds, WallClock

from app.contracts.analytics import RecordProductEventFacilitatorContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.analytics_repositories import (
    WebVitalSampleRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.analytics import (
    ProductEventName,
    ProductEventSource,
    TunnelStepAction,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.product_events import ProductEventProperties
from app.schemas.domain.web_vitals import WebVitalSampleDocument
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft
from app.schemas.dto.analytics.telemetry import (
    TelemetryBatchCommand,
    TelemetryBatchReceipt,
    TunnelStepReport,
    WebVitalReport,
)
from app.schemas.dto.rate_limits import RateLimitCounter
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.analytics.constrained_integers import TelemetryReportCount
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import (
    RateWindowSeconds,
    RequestsPerWindow,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey

TELEMETRY_WINDOW: RateWindowSeconds = RateWindowSeconds(60)
# A page reports its vitals once or twice and the tunnel a step at a time;
# thirty batches a minute is far above a person and far below a flood.
TELEMETRY_BATCHES_PER_WINDOW: RequestsPerWindow = RequestsPerWindow(30)
TUNNEL_EVENTS: dict[TunnelStepAction, ProductEventName] = {
    TunnelStepAction.ENTERED: ProductEventName.TUNNEL_STEP_ENTERED,
    TunnelStepAction.COMPLETED: ProductEventName.TUNNEL_STEP_COMPLETED,
}


class RecordTelemetryUseCase(
    UseCaseContract[TelemetryBatchCommand, TelemetryBatchReceipt]
):
    """
    Keep a signed-in person's batch of cabinet reports: Web Vitals as
    samples (one write per batch; purged after 90 days) and tunnel steps as
    product events of the cabinet. At most 30 batches a minute per person
    (shared by every API instance). A tunnel step names its business only
    when the person is on its team; otherwise it is kept without it.
    """

    def __init__(
        self,
        web_vital_sample_repo: WebVitalSampleRepoContract,
        business_repo: BusinessRepoContract,
        product_events: RecordProductEventFacilitatorContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._web_vital_sample_repo: WebVitalSampleRepoContract = web_vital_sample_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._product_events: RecordProductEventFacilitatorContract = product_events
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: TelemetryBatchCommand) -> TelemetryBatchReceipt:
        now: Microseconds = self._wall_clock.now_unix()
        counter = RateLimitCounter(
            key=RateLimitKey(f"telemetry:user:{input_data.user_id}"),
            limit=TELEMETRY_BATCHES_PER_WINDOW,
        )
        if self._rate_limit_registry.try_acquire_all([counter], TELEMETRY_WINDOW, now):
            raise RateLimitedError(
                "Too many telemetry reports. Try again in a minute.",
                retry_after_seconds=self._rate_limit_registry.seconds_until_free(
                    counter, TELEMETRY_WINDOW, now
                ),
            )

        vitals: list[WebVitalSampleDocument] = [
            WebVitalSampleDocument(
                user_id=input_data.user_id,
                metric=report.metric,
                value=report.value,
                route=report.route,
                device_class=report.device_class,
                created_at=now,
                updated_at=now,
            )
            for report in input_data.events
            if isinstance(report, WebVitalReport)
        ]
        if vitals:
            self._web_vital_sample_repo.add_many(vitals)

        steps: list[TunnelStepReport] = [
            report
            for report in input_data.events
            if isinstance(report, TunnelStepReport)
        ]
        teams: set[BusinessId] = self._own_businesses(input_data, steps)
        self._product_events.record(
            *(
                ProductEventDraft(
                    name=TUNNEL_EVENTS[step.action],
                    user_id=input_data.user_id,
                    business_id=step.business_id if step.business_id in teams else None,
                    properties=ProductEventProperties(tunnel_step=step.step),
                    source=ProductEventSource.CABINET,
                )
                for step in steps
            )
        )
        return TelemetryBatchReceipt(
            web_vitals=TelemetryReportCount(len(vitals)),
            tunnel_steps=TelemetryReportCount(len(steps)),
        )

    def _own_businesses(
        self, command: TelemetryBatchCommand, steps: list[TunnelStepReport]
    ) -> set[BusinessId]:
        """The named businesses the person is on the team of."""

        named: set[BusinessId] = {
            step.business_id for step in steps if step.business_id is not None
        }
        teams: set[BusinessId] = set()
        for business_id in named:
            business: BusinessDocument | None = self._business_repo.get(business_id)
            if business is not None and any(
                member.user_id == command.user_id for member in business.members
            ):
                teams.add(business_id)

        return teams
