"""What the reply guard did, counted by the database (admin health, brake)."""

from typed_time_provider import Microseconds

from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    AUTHOR_FIELD,
    CONVERSATION_ID_FIELD,
    CREATED_AT_FIELD,
    DIRECTION_FIELD,
)
from app.repositories.document_queries import field_equals, time_range
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.reply_safety import ClientGuardActivity
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.constrained_integers import (
    GuardedReplyCount,
    InjectionFlagCount,
)
from app.schemas.typings.conversations.constrained_integers import (
    ConversationMessageCount,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

GUARD_VERDICT_FIELD: DocumentFieldPath = DocumentFieldPath("guard_verdict")
INJECTION_FLAG_FIELD: DocumentFieldPath = DocumentFieldPath("injection_flag")


class GuardActivityReading(BusinessScopedRepository[MessageDocument]):
    """
    The reply guard's work in the messages: replies per verdict and flagged
    customer messages of a period in one grouped count (the period through
    `messages_doc_created_at_idx`; the guard columns of 1102), and one
    conversation's flagged messages (its indexed transcript, narrowed by
    the flag).
    """

    def count_guard_activity(
        self, business_id: BusinessId, since: Microseconds
    ) -> ClientGuardActivity:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    ranges=(time_range(CREATED_AT_FIELD, starting_at=since),)
                ),
                group_by=(AUTHOR_FIELD, GUARD_VERDICT_FIELD, INJECTION_FLAG_FIELD),
            ),
        )
        verdicts: dict[ReplyGuardVerdict, int] = dict.fromkeys(ReplyGuardVerdict, 0)
        flags: int = 0
        for group in groups:
            author_text, verdict_text, flag_text = group.values
            author: MessageAuthor | None = parse_choice(MessageAuthor, author_text)
            verdict: ReplyGuardVerdict | None = parse_choice(
                ReplyGuardVerdict, verdict_text
            )
            if author is MessageAuthor.ASSISTANT and verdict is not None:
                verdicts[verdict] += int(group.count)

            if author is MessageAuthor.CUSTOMER and flag_text is not None:
                flags += int(group.count)

        return ClientGuardActivity(
            checked_replies=GuardedReplyCount(sum(verdicts.values())),
            rewritten_replies=GuardedReplyCount(verdicts[ReplyGuardVerdict.REWRITTEN]),
            handed_off_replies=GuardedReplyCount(
                verdicts[ReplyGuardVerdict.HANDED_OFF]
            ),
            injection_flags=InjectionFlagCount(flags),
        )

    def count_injection_flags(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        created_from: Microseconds,
    ) -> ConversationMessageCount:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(
                        field_equals(CONVERSATION_ID_FIELD, conversation_id),
                        field_equals(DIRECTION_FIELD, MessageDirection.INBOUND),
                    ),
                    ranges=(time_range(CREATED_AT_FIELD, starting_at=created_from),),
                ),
                group_by=(INJECTION_FLAG_FIELD,),
            ),
        )
        return ConversationMessageCount(
            sum(int(group.count) for group in groups if group.values[0] is not None)
        )
