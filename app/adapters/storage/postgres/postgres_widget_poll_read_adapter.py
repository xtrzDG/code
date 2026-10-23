from psycopg.rows import TupleRow
from typed_time_provider import Microseconds

from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.adapters.storage.postgres.platform_transaction import (
    read_document_text,
    storage_errors_translated,
)
from app.adapters.storage.postgres.read_sessions import read_session_connection
from app.adapters.storage.postgres.scoped_transactions import fetch_in_scope
from app.adapters.storage.postgres.widget_poll_read_queries import (
    CONVERSATION_ROW,
    MESSAGE_ROW,
    ORIGINS_ROW,
    WIDGET_POLL_READ,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.storage import StorageScopeContract
from app.contracts.widget_poll_reads import WidgetPollReadAdapterContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.business_limits import BusinessLimitsDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget_poll_reads import WidgetPollRead
from app.schemas.dto.message_positions import MessagePosition
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.spend.spend_keys import business_limits_id_of
from app.utilities.storage.storage_scoping import require_tenant_scope

WIDGET_POLL_LABEL: str = "widget poll"


class PostgresWidgetPollReadAdapter(WidgetPollReadAdapterContract):
    """
    A widget poll's reads as one statement (`widget_poll_read_queries`) in
    one round trip: on an idle connection the scope and the statement are
    pipelined into one implicit transaction (`fetch_in_scope`); inside a
    read session the statement joins its transaction. Row-level security
    binds it in the ambient scope, and every table is also filtered by the
    business asked for, like the repositories' reads.

    Documents decode with their collections' codecs (upcasting older rows).
    The statement chooses the shown conversations by their lookup columns;
    when the decoded documents disagree (a row an upcaster changes), the
    positions are not used (`newest` is None) and the poll reads the whole
    chat through its repositories.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContract,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._storage_scope: StorageScopeContract = storage_scope
        self._limits_codec: PersistedDocumentCodec[BusinessLimitsDocument] = (
            PersistedDocumentCodec(
                BusinessLimitsDocument, DocumentCollectionName("business_limits")
            )
        )
        self._conversation_codec: PersistedDocumentCodec[ConversationDocument] = (
            PersistedDocumentCodec(
                ConversationDocument, DocumentCollectionName("conversations")
            )
        )
        self._message_codec: PersistedDocumentCodec[MessageDocument] = (
            PersistedDocumentCodec(MessageDocument, DocumentCollectionName("messages"))
        )

    def read_poll(
        self,
        business_id: BusinessId,
        visitor: ChannelUserId,
        after: MessageId | None,
        window: KeysetReadLimit,
    ) -> WidgetPollRead:
        scope: StorageScope = require_tenant_scope(
            self._storage_scope.current(), WIDGET_POLL_LABEL
        )
        parameters: dict[str, object] = {
            "business_id": str(business_id),
            "visitor": str(visitor),
            "web_chat": ChannelKind.WEB_CHAT.value,
            "limits_key": str(business_limits_id_of(business_id)),
            "window": int(window),
            "after": None if after is None else str(after),
        }
        with storage_errors_translated(WIDGET_POLL_LABEL):
            with read_session_connection(self._connection_pool, scope) as connection:
                if connection is not None:
                    return self._decode(
                        connection.execute(WIDGET_POLL_READ, parameters).fetchall()
                    )

            return self._decode(
                fetch_in_scope(
                    self._connection_pool, scope, WIDGET_POLL_READ, parameters
                )
            )

    def _decode(self, rows: list[TupleRow]) -> WidgetPollRead:
        origins: list[PublicBaseUrl] = []
        placed: list[tuple[int, ConversationDocument]] = []
        shown_by_statement: set[ConversationId] = set()
        newest: list[MessagePosition] = []
        after_cursor: list[MessageDocument] = []
        for kind, position, document_key, is_shown, document_text in rows:
            if kind == ORIGINS_ROW:
                origins = self._limits_codec.decode(
                    read_document_text((document_text,), WIDGET_POLL_LABEL)
                ).widget_allowed_origins
            elif kind == CONVERSATION_ROW:
                conversation: ConversationDocument = self._conversation_codec.decode(
                    read_document_text((document_text,), WIDGET_POLL_LABEL)
                )
                placed.append((read_position(position), conversation))
                if is_shown is True:
                    shown_by_statement.add(conversation.id)
            elif kind == MESSAGE_ROW:
                newest.append(
                    MessagePosition(
                        id=MessageId(str(document_key)),
                        created_at=Microseconds(read_position(position)),
                    )
                )
                if document_text is not None:
                    after_cursor.append(
                        self._message_codec.decode(
                            read_document_text((document_text,), WIDGET_POLL_LABEL)
                        )
                    )

        shown: list[ConversationDocument] = [
            conversation
            for _, conversation in sorted(placed, key=lambda entry: entry[0])
            if conversation.channel is ChannelKind.WEB_CHAT
            and not conversation.is_sandbox
        ]
        agrees: bool = shown_by_statement == {conversation.id for conversation in shown}
        return WidgetPollRead(
            allowed_origins=origins,
            conversations=shown,
            newest=newest if agrees else None,
            after_cursor=(sorted(after_cursor, key=answer_order) if agrees else []),
        )


def answer_order(message: MessageDocument) -> tuple[int, str]:
    """The order a poll answers in: by creation time, ties by id."""

    return (int(message.created_at), str(message.id))


def read_position(value: object) -> int:
    """A place or a creation time (`bigint`) of the poll's statement."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise ExternalServiceError(
            f"The {WIDGET_POLL_LABEL} statement returned a position that is not "
            f"an integer ({type(value).__name__})."
        )

    return value
