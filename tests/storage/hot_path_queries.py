"""The hot queries of the repositories and the index each one must use."""

from collections.abc import Callable
from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId, ManagerLinkCodeHash
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId, ProviderCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessTokenHash
from tests.storage.hot_path_repositories import HotPathRepositories
from tests.storage.hot_path_rows import BASE_TIME, BUSINESS_COUNT

INDEX_NODE_TYPES: frozenset[str] = frozenset(
    {"Index Scan", "Index Only Scan", "Bitmap Index Scan"}
)
BUSINESS_IDS: list[BusinessId] = [BusinessId() for _ in range(BUSINESS_COUNT)]
NOW = Microseconds(BASE_TIME + 2_000)
LOOKUP_KEYS = "document_lookup_keys_pkey"


@dataclass(frozen=True)
class HotQuery:
    """A repository call of a hot path and the index its SQL must use."""

    name: str
    run: Callable[[HotPathRepositories], object]
    table: str
    index: str
    is_in_business_scope: bool = True
    # Other indexes the planner may rightly prefer for this query.
    alternative_indexes: tuple[str, ...] = ()


HOT_QUERIES: tuple[HotQuery, ...] = (
    HotQuery(
        "session by token hash (every signed-in request)",
        lambda r: r.sessions.find_by_token_hash(AccessTokenHash("f" * 64)),
        "user_sessions",
        "user_sessions_doc_token_hash_idx",
        is_in_business_scope=False,
    ),
    HotQuery(
        "user by phone",
        lambda r: r.users.find_by_phone_number(E164PhoneNumber("+15559999999")),
        "users",
        "users_doc_phone_number_idx",
        is_in_business_scope=False,
    ),
    HotQuery(
        "user by e-mail",
        lambda r: r.users.find_by_email(EmailAddress("someone@example.org")),
        "users",
        "users_doc_email_idx",
        is_in_business_scope=False,
    ),
    HotQuery(
        "login codes of the last hour",
        lambda r: r.challenges.list_created_since(Microseconds(BASE_TIME + 4_000_000)),
        "otp_challenges",
        "otp_challenges_doc_created_at_idx",
        is_in_business_scope=False,
    ),
    HotQuery(
        "businesses of a member",
        lambda r: r.businesses.list_by_member(UserId()),
        "document_lookup_keys",
        LOOKUP_KEYS,
        is_in_business_scope=False,
    ),
    HotQuery(
        "channel of an incoming webhook",
        lambda r: r.channels.find_by_external_id(
            ChannelKind.TELEGRAM, ChannelExternalId("external_77777")
        ),
        "channels",
        "channels_doc_kind_external_id_idx",
        is_in_business_scope=False,
    ),
    HotQuery(
        "contact by channel identity",
        lambda r: r.contacts.find_by_channel_identity(
            BUSINESS_IDS[0], ChannelKind.TELEGRAM, ChannelUserId("tg_unknown")
        ),
        "document_lookup_keys",
        LOOKUP_KEYS,
    ),
    HotQuery(
        "contact by proved phone",
        lambda r: r.contacts.find_by_verified_phone_number(
            BUSINESS_IDS[0], E164PhoneNumber("+995555999999")
        ),
        "contacts",
        "contacts_doc_verified_phone_number_idx",
    ),
    HotQuery(
        "handoff conversations of a contact",
        lambda r: r.conversations.list_by_contact(
            BUSINESS_IDS[0], ContactId(), status=ConversationStatus.HANDOFF
        ),
        "conversations",
        "conversations_doc_contact_idx",
        # Few conversations wait for a person: the inbox's status index
        # (1053) can be the cheaper start.
        alternative_indexes=("conversations_doc_status_last_message_at_idx",),
    ),
    HotQuery(
        "recent conversations of a contact",
        lambda r: r.conversations.list_by_contact(
            BUSINESS_IDS[0], ContactId(), last_message_from=NOW
        ),
        "conversations",
        "conversations_doc_contact_idx",
    ),
    HotQuery(
        "widget visitor's conversations",
        lambda r: r.conversations.list_by_channel_user(
            BUSINESS_IDS[0], ChannelKind.WEB_CHAT, ChannelUserId("tg_unknown")
        ),
        "conversations",
        "conversations_doc_channel_user_idx",
    ),
    HotQuery(
        "recent inbound count of a conversation",
        lambda r: r.messages.count_by_conversation(
            BUSINESS_IDS[0],
            ConversationId(),
            MessageDirection.INBOUND,
            created_from=NOW,
        ),
        "messages",
        "messages_doc_conversation_idx",
    ),
    HotQuery(
        "assistant replies of a conversation",
        lambda r: r.messages.count_by_conversation(
            BUSINESS_IDS[0],
            ConversationId(),
            MessageDirection.OUTBOUND,
            author=MessageAuthor.ASSISTANT,
        ),
        "messages",
        "messages_doc_conversation_idx",
    ),
    HotQuery(
        "transcript of a conversation",
        lambda r: r.messages.list_by_conversation(BUSINESS_IDS[0], ConversationId()),
        "messages",
        "messages_doc_conversation_idx",
    ),
    HotQuery(
        "model turns of a conversation",
        lambda r: r.turns.list_by_conversation(ConversationId()),
        "llm_turns",
        "llm_turns_doc_conversation_idx",
        is_in_business_scope=False,
    ),
    HotQuery(
        "call by provider id",
        lambda r: r.calls.find_by_provider_call_id(
            BUSINESS_IDS[0], ProviderCallId("call_unknown")
        ),
        "calls",
        "calls_doc_provider_call_id_idx",
    ),
    HotQuery(
        "manager link by code",
        lambda r: r.manager_links.find_by_code_hash(ManagerLinkCodeHash("0" * 64)),
        "manager_telegram_links",
        "manager_telegram_links_doc_code_hash_idx",
        is_in_business_scope=False,
    ),
    HotQuery(
        "usage of a billing period",
        lambda r: r.usage_events.list_by_business_between(
            BUSINESS_IDS[0],
            Microseconds(BASE_TIME + 4_100_000),
            Microseconds(BASE_TIME + 4_200_000),
        ),
        "usage_events",
        "usage_events_doc_occurred_at_idx",
    ),
    HotQuery(
        "purge of expired sessions",
        lambda r: r.sessions.delete_expired(Microseconds(BASE_TIME + 3)),
        "user_sessions",
        "user_sessions_doc_expires_at_idx",
        is_in_business_scope=False,
        # The second delete (sessions unused too long, 1103) uses its own.
        alternative_indexes=("user_sessions_doc_idle_expires_at_idx",),
    ),
    HotQuery(
        "purge of old login codes",
        lambda r: r.challenges.delete_created_before(Microseconds(BASE_TIME + 3_000)),
        "otp_challenges",
        "otp_challenges_doc_created_at_idx",
        is_in_business_scope=False,
    ),
    HotQuery(
        "purge of old receipts",
        lambda r: r.receipts.delete_created_before(Microseconds(BASE_TIME + 3)),
        "channel_message_receipts",
        "channel_message_receipts_doc_created_at_idx",
        is_in_business_scope=False,
    ),
)
