"""The repositories of the hot paths, over Postgres collections of one pool."""

from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.billing_repositories import UsageEventRepository
from app.repositories.business_repositories import (
    BusinessRepository,
    ChannelRepository,
)
from app.repositories.channel_repositories import (
    ChannelMessageReceiptRepository,
    ManagerTelegramLinkRepository,
)
from app.repositories.conversation_repositories import (
    CallRepository,
    ContactRepository,
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserRepository,
    UserSessionRepository,
)
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.storage_testing import build_fixed_wall_clock


class HotPathRepositories:
    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContext,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._storage_scope: StorageScopeContext = storage_scope
        self.users = UserRepository(self._collection(UserDocument, "users"))
        self.sessions = UserSessionRepository(
            self._collection(UserSessionDocument, "user_sessions")
        )
        self.challenges = OtpChallengeRepository(
            self._collection(OtpChallengeDocument, "otp_challenges")
        )
        self.businesses = BusinessRepository(
            self._collection(BusinessDocument, "businesses")
        )
        self.channels = ChannelRepository(self._collection(ChannelDocument, "channels"))
        self.contacts = ContactRepository(self._collection(ContactDocument, "contacts"))
        self.conversations = ConversationRepository(
            self._collection(ConversationDocument, "conversations")
        )
        self.messages = MessageRepository(self._collection(MessageDocument, "messages"))
        self.turns = LlmTurnRepository(self._collection(LlmTurnDocument, "llm_turns"))
        self.calls = CallRepository(self._collection(CallDocument, "calls"))
        self.usage_events = UsageEventRepository(
            self._collection(UsageEventDocument, "usage_events")
        )
        self.manager_links = ManagerTelegramLinkRepository(
            self._collection(ManagerTelegramLinkDocument, "manager_telegram_links")
        )
        self.receipts = ChannelMessageReceiptRepository(
            self._collection(ChannelMessageReceiptDocument, "channel_message_receipts")
        )

    def _collection[StoredDocument: PersistentDocument](
        self,
        document_type: type[StoredDocument],
        collection_name: str,
    ) -> PostgresDocumentCollectionAdapter[StoredDocument]:
        return PostgresDocumentCollectionAdapter[StoredDocument](
            document_type=document_type,
            collection_name=DocumentCollectionName(collection_name),
            connection_pool=self._connection_pool,
            storage_scope=self._storage_scope,
            wall_clock=build_fixed_wall_clock(),
            isolation=infer_collection_isolation(document_type),
        )
