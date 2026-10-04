"""Routers of the guided launch: setup, starter answers, autosave, apply changes."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.apply_changes_routes import build_apply_changes_router
from app.gateways.http.setup_guide_routes import build_setup_guide_router
from app.gateways.http.setup_routes import build_setup_router
from app.gateways.http.starter_routes import build_starter_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_launch_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """The routers that take an owner from nothing to a live assistant."""

    setup = operators.setup
    return [
        build_setup_router(
            current_user=current_user,
            create_business_operator=operators.accounts.create_business_operator(),
            get_setup_progress_operator=setup.get_setup_progress_operator(),
            skip_setup_step_operator=setup.skip_setup_step_operator(),
            celebrate_milestone_operator=setup.celebrate_milestone_operator(),
            get_starter_answers_operator=setup.get_starter_answers_operator(),
        ),
        build_setup_guide_router(
            current_user=current_user,
            start_phone_check_operator=setup.start_phone_check_operator(),
            mark_setup_shared_operator=setup.mark_setup_shared_operator(),
            dismiss_setup_guide_operator=setup.dismiss_setup_guide_operator(),
            get_setup_reminders_operator=setup.get_setup_reminders_operator(),
            update_setup_reminders_operator=setup.update_setup_reminders_operator(),
        ),
        build_starter_router(
            current_user=current_user,
            get_starter_answers_operator=setup.get_starter_answers_operator(),
            apply_starter_answers_operator=setup.apply_starter_answers_operator(),
            patch_profile_operator=setup.patch_profile_operator(),
        ),
        build_apply_changes_router(
            current_user=current_user,
            apply_changes_operator=operators.assistants.apply_changes_operator(),
            get_apply_changes_operator=operators.assistants.get_apply_changes_operator(),
            get_pending_changes_operator=operators.assistants.get_pending_changes_operator(),
        ),
    ]
