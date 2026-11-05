"""
Routers of the platform's own operations: the job queue, system, incidents,
post-deploy data tasks.
"""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_campaign_hold_routes import (
    build_admin_campaign_hold_router,
)
from app.gateways.http.admin_data_task_routes import build_admin_data_task_router
from app.gateways.http.admin_feature_flag_routes import (
    build_admin_feature_flag_router,
)
from app.gateways.http.admin_jobs_routes import build_admin_jobs_router
from app.gateways.http.admin_ops_routes import build_admin_ops_router
from app.gateways.http.error_budget_routes import build_error_budget_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_admin_ops_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """
    /v1/admin/jobs, GET /v1/admin/system (its error budget and data tasks),
    /v1/admin/incidents, /v1/admin/campaign-holds and
    /v1/admin/feature-flags.
    """

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
            create_incident_operator=operators.reliability.record_incident_operator(),
            list_incidents_operator=platform_ops.list_incidents_operator(),
            current_user=current_user,
        ),
        build_admin_data_task_router(
            get_data_tasks_operator=operators.data_tasks.get_data_tasks_operator(),
            retry_data_task_operator=operators.data_tasks.retry_data_task_operator(),
            current_user=current_user,
        ),
        build_error_budget_router(
            get_error_budget_operator=operators.telemetry.get_error_budget_operator(),
            current_user=current_user,
        ),
        build_admin_campaign_hold_router(
            current_user=current_user,
            list_campaign_holds=platform.list_campaign_holds_operator(),
            release_campaign_hold=platform.release_campaign_hold_operator(),
        ),
        build_admin_feature_flag_router(
            current_user=current_user,
            list_feature_flags=operators.spend_guard.list_feature_flags_operator(),
            set_feature_flag=operators.spend_guard.set_feature_flag_operator(),
            check_feature_flag=operators.spend_guard.check_feature_flag_operator(),
        ),
    ]
