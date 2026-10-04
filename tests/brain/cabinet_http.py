"""The brain's cabinet routes on a small FastAPI app, wired like production."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.brain import MenuExtractionAdapterContract
from app.gateways.http.conversation_routes import build_conversation_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.menu_import_routes import build_menu_import_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.brain.brain_world import BrainWorld
from tests.brain.cabinet_fakes import CabinetStorage, TokenAuthenticationOperator
from tests.brain.cabinet_operators import CabinetOperators, build_cabinet_operators


def build_cabinet_client(
    world: BrainWorld,
    menu_extractor: MenuExtractionAdapterContract,
    users_by_token: dict[str, UserId],
    storage: CabinetStorage | None = None,
) -> TestClient:
    operators: CabinetOperators = build_cabinet_operators(
        world, menu_extractor, storage or CabinetStorage()
    )
    current_user = build_current_user_dependency(
        TokenAuthenticationOperator(users_by_token), SessionAssuranceContext()
    )
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_conversation_router(
            list_conversations_operator=operators.list_conversations,
            get_conversation_operator=operators.get_conversation,
            owner_test_chat_operator=operators.owner_test_chat,
            rate_conversation_operator=operators.rate_conversation,
            current_user=current_user,
            send_staff_message_operator=operators.send_staff_message,
            get_call_recording_operator=operators.get_call_recording,
            list_conversation_messages_operator=operators.list_conversation_messages,
        )
    )
    http_application.include_router(
        build_menu_import_router(
            import_menu_operator=operators.import_menu,
            confirm_imported_items_operator=operators.confirm_imported_items,
            discard_import_batch_operator=operators.discard_import_batch,
            current_user=current_user,
        )
    )
    return TestClient(http_application)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
