"""Readiness of this API instance for the load balancer: GET /readyz."""

import logging

import anyio
import anyio.to_thread
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.contracts.operator_contract import OperatorContract
from app.schemas.constants.observability import (
    DatabaseProbeFailure,
    HealthCheckStatus,
    ReadinessState,
)
from app.schemas.dto.health import ReadinessQuery, ReadinessReport

LOGGER: logging.Logger = logging.getLogger(__name__)
READINESS_PATH: str = "/readyz"
# The probe itself gives up after 2 s; past this the answer is "not ready".
READINESS_DEADLINE_SECONDS: float = 3.0
# Readiness checks run on threads of their own, never on the request
# threads: a busy API (every request thread taken) still answers.
READINESS_THREADS: int = 2
HTTP_OK: int = 200
HTTP_SERVICE_UNAVAILABLE: int = 503


def build_readiness_router(
    readiness_operator: OperatorContract[ReadinessQuery, ReadinessReport],
) -> APIRouter:
    """
    Route (no bearer token, not in the API description):
        GET /readyz    200 while the instance can serve: the database answers
                       and every migration of this build is applied; a pool
                       busy with load is DEGRADED and keeps the traffic
                       unless it stays exhausted for more than 30 s. 503
                       otherwise. The body names each check, and the age of
                       the freshest worker heartbeat (reported only).

    Render routes traffic by this one (`healthCheckPath: /readyz` in
    render.yaml and render.staging.yaml) and takes an instance out of
    rotation while it answers 503. `GET /healthz` (liveness, in
    `application.py`) never touches the database.
    """

    router = APIRouter()
    limiters: list[anyio.CapacityLimiter] = []

    @router.get(READINESS_PATH, include_in_schema=False)
    async def check_readiness() -> JSONResponse:
        if not limiters:
            limiters.append(anyio.CapacityLimiter(READINESS_THREADS))
        report: ReadinessReport | None = None
        with anyio.move_on_after(READINESS_DEADLINE_SECONDS):
            report = await anyio.to_thread.run_sync(
                readiness_operator.operate,
                ReadinessQuery(),
                abandon_on_cancel=True,
                limiter=limiters[0],
            )

        if report is None:
            LOGGER.warning(
                "Readiness check took longer than %.0f s", READINESS_DEADLINE_SECONDS
            )
            return JSONResponse(
                status_code=HTTP_SERVICE_UNAVAILABLE,
                content={
                    "status": ReadinessState.NOT_READY.value,
                    "checks": {
                        "database": {
                            "status": HealthCheckStatus.FAILED.value,
                            "failure": DatabaseProbeFailure.TIMEOUT.value,
                        }
                    },
                },
            )

        return JSONResponse(
            status_code=(
                HTTP_OK
                if report.status is ReadinessState.READY
                else HTTP_SERVICE_UNAVAILABLE
            ),
            content=report.model_dump(mode="json", exclude_none=True),
        )

    return router
