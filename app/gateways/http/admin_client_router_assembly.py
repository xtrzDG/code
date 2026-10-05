"""Routers of the admin that acts on a client's account and keeps its story."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_account_action_routes import (
    build_admin_account_action_router,
)
from app.gateways.http.admin_client_story_routes import (
    build_admin_client_story_router,
)
from app.gateways.http.user_authentication import CurrentUserDependency


def build_admin_client_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """The account actions, notes, timeline and the done-for-you request."""

    actions = operators.admin_actions
    return [
        build_admin_account_action_router(
            extend_trial_operator=actions.extend_trial_operator(),
            give_discount_operator=actions.give_discount_operator(),
            grant_credit_operator=actions.grant_credit_operator(),
            waive_setup_fee_operator=actions.waive_setup_fee_operator(),
            mark_invoice_paid_operator=actions.mark_invoice_paid_operator(),
            override_plan_operator=actions.override_plan_operator(),
            current_user=current_user,
        ),
        build_admin_client_story_router(
            list_notes_operator=actions.list_client_notes_operator(),
            create_note_operator=actions.create_client_note_operator(),
            update_note_operator=actions.update_client_note_operator(),
            delete_note_operator=actions.delete_client_note_operator(),
            timeline_operator=actions.get_client_timeline_operator(),
            complete_onboarding_operator=actions.complete_onboarding_operator(),
            current_user=current_user,
        ),
    ]
