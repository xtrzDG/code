"""GET /healthz/pipeline: whether the workers answer customers (outside monitor)."""

import logging

import anyio
import anyio.to_thread
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.contracts.operator_contract import OperatorContract
from app.schemas.constants.observability import PipelineState
from app.schemas.dto.pipeline_health import PipelineHealthQuery, PipelineHealthReport
from app.utilities.monitoring.pipeline_health import unreadable_pipeline

LOGGER: logging.Logger = logging.getLogger(__name__)
PIPELINE_HEALTH_PATH: str = "/healthz/pipeline"
# Three indexed reads; past this the database cannot tell (503).
PIPELINE_DEADLINE_SECONDS: float = 3.0
# Probes run on threads of their own, never on the request threads: a
# busy API still answers its monitor.
PIPELINE_THREADS: int = 1
HTTP_OK: int = 200
HTTP_SERVICE_UNAVAILABLE: int = 503
NO_STORE: dict[str, str] = {"Cache-Control": "no-store"}


def build_pipeline_health_router(
    pipeline_health_operator: OperatorContract[
        PipelineHealthQuery, PipelineHealthReport
    ],
) -> APIRouter:
    """
    Route (no bearer token, not in the API description):
        GET /healthz/pipeline   200 while customers' messages flow: a worker
                                pulsed within 5 min and no due customer
                                message waited more than 120 s. 503
                                otherwise, or when the database cannot
                                tell in 3 s. The body names both checks.

    The external uptime monitor's second check beside GET /readyz
    (docs/operations/slo.md, ops/alerts/stale_worker.yaml): /readyz says
    whether this API instance serves, this one whether the workers behind
    it answer customers. Render never routes traffic by it.
    """

    router = APIRouter()
    limiters: list[anyio.CapacityLimiter] = []

    @router.get(PIPELINE_HEALTH_PATH, include_in_schema=False)
    async def check_pipeline() -> JSONResponse:
        if not limiters:
            limiters.append(anyio.CapacityLimiter(PIPELINE_THREADS))
        report: PipelineHealthReport | None = None
        with anyio.move_on_after(PIPELINE_DEADLINE_SECONDS):
            report = await anyio.to_thread.run_sync(
                pipeline_health_operator.operate,
                PipelineHealthQuery(),
                abandon_on_cancel=True,
                limiter=limiters[0],
            )

        if report is None:
            LOGGER.warning(
                "The pipeline check took longer than %.0f s",
                PIPELINE_DEADLINE_SECONDS,
            )
            report = unreadable_pipeline()

        return JSONResponse(
            status_code=(
                HTTP_OK
                if report.status is PipelineState.FLOWING
                else HTTP_SERVICE_UNAVAILABLE
            ),
            content=report.model_dump(mode="json", exclude_none=True),
            headers=NO_STORE,
        )

    return router
