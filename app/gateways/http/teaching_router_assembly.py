"""Routers of teaching the assistant from real conversations."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.answer_fix_routes import build_answer_fix_router
from app.gateways.http.autotest_case_routes import build_autotest_case_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_teaching_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """
    "Fix this answer", the answers worth improving, and the owner's own
    checks every autotest run plays.
    """

    conversations = operators.conversations
    assistants = operators.assistants
    return [
        build_answer_fix_router(
            current_user=current_user,
            get_correction_draft=conversations.get_answer_correction_draft_operator(),
            correct_answer=conversations.correct_answer_operator(),
            list_answers_to_improve=conversations.list_answers_to_improve_operator(),
        ),
        build_autotest_case_router(
            current_user=current_user,
            list_cases=assistants.list_autotest_cases_operator(),
            create_case=assistants.create_autotest_case_operator(),
            update_case=assistants.update_autotest_case_operator(),
            delete_case=assistants.delete_autotest_case_operator(),
        ),
    ]
