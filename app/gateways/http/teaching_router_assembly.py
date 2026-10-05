"""Routers of teaching the assistant from real conversations and of
measuring how good they are (production quality)."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.answer_fix_routes import build_answer_fix_router
from app.gateways.http.autotest_case_routes import build_autotest_case_router
from app.gateways.http.quality_routes import build_quality_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_teaching_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """
    "Fix this answer", the answers worth improving, the owner's own
    checks every autotest run plays, and the judge's scores of real
    conversations (a client's trend, a conversation's score).
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
        build_quality_router(
            current_user=current_user,
            get_client_quality=operators.platform_ops.get_client_quality_operator(),
            get_conversation_quality=(
                conversations.get_conversation_quality_operator()
            ),
        ),
    ]
