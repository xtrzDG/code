"""Readiness of this API instance for the load balancer: GET /readyz."""

import logging
import time
from dataclasses import dataclass

import anyio
import anyio.to_thread
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.middleware.flood_budgets import MonotonicClock
from app.gateways.http.network_budget_dependency import build_network_budget
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
# Probes within this long share one check: a flood of probes costs the
# database one round trip every two seconds, whatever its size.
READINESS_ANSWER_SECONDS: float = 2.0
# Probes from the internet, per client network a minute (Render's own
# check comes from its private network and is never counted).
READINESS_PROBES_PER_MINUTE: int = 60
READINESS_REFUSAL: str = "Too many readiness probes; try again in a moment."


@dataclass
class ReadinessAnswer:
    status_code: int
    content: dict[str, object]
    checked_at: float


def build_readiness_router(
    readiness_operator: OperatorContract[ReadinessQuery, ReadinessReport],
    clock: MonotonicClock = time.monotonic,
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
    `application.py`) never touches the database. Probes within 2 s share
    one check (one runs at a time), and a client network of the internet
    may probe 60 times a minute (429 past it; private addresses, where
    Render's check comes from, are never counted).
    """

    router = APIRouter()
    limiters: list[anyio.CapacityLimiter] = []
    locks: list[anyio.Lock] = []
    answers: list[ReadinessAnswer] = []
    probe_budget = build_network_budget(
        "readyz",
        READINESS_PROBES_PER_MINUTE,
        READINESS_REFUSAL,
        spare_private_networks=True,
        clock=clock,
    )

    @router.get(
        READINESS_PATH, include_in_schema=False, dependencies=[Depends(probe_budget)]
    )
    async def check_readiness() -> JSONResponse:
        if not locks:
            locks.append(anyio.Lock())
        async with locks[0]:
            if not answers or (
                clock() - answers[0].checked_at >= READINESS_ANSWER_SECONDS
            ):
                answers[:] = [await check_now()]

        answer: ReadinessAnswer = answers[0]
        return JSONResponse(status_code=answer.status_code, content=answer.content)

    async def check_now() -> ReadinessAnswer:
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
            return ReadinessAnswer(
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
                checked_at=clock(),
            )

        return ReadinessAnswer(
            status_code=(
                HTTP_OK
                if report.status is ReadinessState.READY
                else HTTP_SERVICE_UNAVAILABLE
            ),
            content=report.model_dump(mode="json", exclude_none=True),
            checked_at=clock(),
        )

    return router
