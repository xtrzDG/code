"""The probes of the outside monitors: is this API ready, do the workers answer."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.health_routes import build_readiness_router
from app.gateways.http.pipeline_health_routes import build_pipeline_health_router


def build_health_routers(operators: OperatorsContainer) -> list[APIRouter]:
    """GET /readyz (this instance serves) and GET /healthz/pipeline (workers)."""

    return [
        build_readiness_router(operators.platform.check_readiness_operator()),
        build_pipeline_health_router(
            operators.reliability.check_pipeline_health_operator()
        ),
    ]
