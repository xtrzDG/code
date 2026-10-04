"""Routers of the platform's own operations: the job queue, system, incidents."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_jobs_routes import build_admin_jobs_router
from app.gateways.http.admin_ops_routes import build_admin_ops_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_admin_ops_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """/v1/admin/jobs, GET /v1/admin/system and /v1/admin/incidents."""

    platform = operators.platform
    platform_ops = operators.platform_ops
    return [
        build_admin_jobs_router(
            list_queued_jobs_operator=platform.list_queued_jobs_operator(),
            retry_queued_job_operator=platform.retry_queued_job_operator(),
            discard_queued_job_operator=platform.discard_queued_job_operator(),
            current_user=current_user,
        ),
        build_admin_ops_router(
            get_admin_system_operator=platform_ops.get_admin_system_operator(),
            create_incident_operator=platform_ops.create_incident_operator(),
            list_incidents_operator=platform_ops.list_incidents_operator(),
            current_user=current_user,
        ),
    ]
