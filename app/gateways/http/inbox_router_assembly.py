"""Routers of the team inbox: views, assignment, notes and saved replies."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.inbox_content_routes import build_inbox_content_router
from app.gateways.http.inbox_routes import build_inbox_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_inbox_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """The routers that let a team share a business's conversations."""

    inbox = operators.inbox
    return [
        build_inbox_router(
            current_user=current_user,
            list_inbox_operator=inbox.list_inbox_operator(),
            count_inbox_views_operator=inbox.count_inbox_views_operator(),
            list_inbox_assignees_operator=inbox.list_inbox_assignees_operator(),
            assign_conversation_operator=inbox.assign_conversation_operator(),
            get_inbox_settings_operator=inbox.get_inbox_settings_operator(),
            update_inbox_settings_operator=inbox.update_inbox_settings_operator(),
        ),
        build_inbox_content_router(
            current_user=current_user,
            create_note_operator=inbox.create_conversation_note_operator(),
            list_notes_operator=inbox.list_conversation_notes_operator(),
            delete_note_operator=inbox.delete_conversation_note_operator(),
            list_quick_replies_operator=inbox.list_quick_replies_operator(),
            save_quick_reply_operator=inbox.save_quick_reply_operator(),
            delete_quick_reply_operator=inbox.delete_quick_reply_operator(),
            fill_quick_replies_operator=inbox.fill_quick_replies_operator(),
        ),
    ]
