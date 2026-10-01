"""The brain's cabinet routes on a small FastAPI app, wired like production."""

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.brain import MenuExtractionAdapterContract
from app.contracts.operator_contract import OperatorContract
from app.gateways.http.conversation_routes import build_conversation_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.menu_import_routes import build_menu_import_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.conversations.owner_test_chat_orchestrator import (
    OwnerTestChatOrchestrator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.conversations.owner_test_chat_pipeline import OwnerTestChatPipeline
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.dto.conversation_feed import (
    ConversationDetailView,
    ConversationListQuery,
    ConversationQuery,
    ConversationSummaryView,
    OwnerTestChatCommand,
    RateConversationCommand,
)
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsResult,
    ImportMenuCommand,
    MenuImportResult,
)
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.transformers.conversations.call_view_transformer import CallViewTransformer
from app.transformers.conversations.conversation_summary_transformer import (
    ConversationSummaryTransformer,
)
from app.transformers.conversations.message_view_transformer import (
    MessageViewTransformer,
)
from app.use_cases.conversations.get_conversation_use_case import (
    GetConversationUseCase,
)
from app.use_cases.conversations.list_conversations_use_case import (
    ListConversationsUseCase,
)
from app.use_cases.conversations.rate_conversation_use_case import (
    RateConversationUseCase,
)
from app.use_cases.conversations.resolve_test_chat_version_use_case import (
    ResolveTestChatVersionUseCase,
)
from app.use_cases.menu_import.confirm_imported_items_use_case import (
    ConfirmImportedItemsUseCase,
)
from app.use_cases.menu_import.import_menu_use_case import ImportMenuUseCase
from tests.brain.brain_world import BrainWorld


class TokenAuthenticationOperator(OperatorContract[AccessToken, UserId]):
    """Bearer token -> user, from a fixed table."""

    def __init__(self, users_by_token: dict[str, UserId]) -> None:
        self._users_by_token: dict[str, UserId] = users_by_token

    def operate(self, input_data: AccessToken) -> UserId:
        user_id: UserId | None = self._users_by_token.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return user_id


@dataclass(frozen=True)
class CabinetOperators:
    list_conversations: OperatorContract[
        ConversationListQuery, list[ConversationSummaryView]
    ]
    get_conversation: OperatorContract[ConversationQuery, ConversationDetailView]
    rate_conversation: OperatorContract[
        RateConversationCommand, ConversationSummaryView
    ]
    owner_test_chat: OperatorContract[OwnerTestChatCommand, AssistantReply]
    import_menu: OperatorContract[ImportMenuCommand, MenuImportResult]
    confirm_imported_items: OperatorContract[
        ConfirmImportedItemsCommand, ConfirmImportedItemsResult
    ]


def build_cabinet_operators(
    world: BrainWorld,
    menu_extractor: MenuExtractionAdapterContract,
) -> CabinetOperators:
    summary_transformer = ConversationSummaryTransformer()
    return CabinetOperators(
        list_conversations=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    ListConversationsUseCase(
                        authorize_business_access=world.authorize,
                        conversation_repo=world.conversation_repo,
                        contact_repo=world.contact_repo,
                        message_repo=world.message_repo,
                        summary_transformer=summary_transformer,
                    )
                )
            )
        ),
        get_conversation=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    GetConversationUseCase(
                        authorize_business_access=world.authorize,
                        conversation_repo=world.conversation_repo,
                        contact_repo=world.contact_repo,
                        message_repo=world.message_repo,
                        audit_log_repo=world.audit_log_repo,
                        summary_transformer=summary_transformer,
                        message_transformer=MessageViewTransformer(),
                        wall_clock=world.clock.wall_clock(),
                        call_repo=world.call_repo,
                        call_transformer=CallViewTransformer(),
                    )
                )
            )
        ),
        rate_conversation=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    RateConversationUseCase(
                        authorize_business_access=world.authorize,
                        conversation_repo=world.conversation_repo,
                        contact_repo=world.contact_repo,
                        message_repo=world.message_repo,
                        summary_transformer=summary_transformer,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        owner_test_chat=PipelineOperator(
            OwnerTestChatPipeline(
                prepare_test_message=OwnerTestChatOrchestrator(
                    authorize_business_access=world.authorize,
                    resolve_test_chat_version=ResolveTestChatVersionUseCase(
                        world.version_repo
                    ),
                ),
                turn_orchestrator=world.orchestrator,
            )
        ),
        import_menu=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    ImportMenuUseCase(
                        authorize_business_access=world.authorize,
                        menu_extraction_adapter=menu_extractor,
                        knowledge_item_repo=world.knowledge_item_repo,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
        confirm_imported_items=PipelineOperator(
            OrchestratorPipeline(
                UseCaseOrchestrator(
                    ConfirmImportedItemsUseCase(
                        authorize_business_access=world.authorize,
                        knowledge_item_repo=world.knowledge_item_repo,
                        wall_clock=world.clock.wall_clock(),
                    )
                )
            )
        ),
    )


def build_cabinet_client(
    world: BrainWorld,
    menu_extractor: MenuExtractionAdapterContract,
    users_by_token: dict[str, UserId],
) -> TestClient:
    operators: CabinetOperators = build_cabinet_operators(world, menu_extractor)
    current_user = build_current_user_dependency(
        TokenAuthenticationOperator(users_by_token)
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
        )
    )
    http_application.include_router(
        build_menu_import_router(
            import_menu_operator=operators.import_menu,
            confirm_imported_items_operator=operators.confirm_imported_items,
            current_user=current_user,
        )
    )
    return TestClient(http_application)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
