"""Transcript pages and database sums of messages."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.repositories.aggregate_reading import parse_choice, period_count
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    AUTHOR_FIELD,
    CONVERSATION_ID_FIELD,
    CREATED_AT_FIELD,
)
from app.repositories.document_queries import (
    field_among,
    field_equals,
    time_range,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.conversation_feed.message_tallies import (
    ConversationMessageTally,
    ConversationUsageView,
)
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFieldAmong, DocumentFilter
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_integers import (
    ConversationMessageCount,
    LlmTokenCount,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.integers import ListSortValue
from app.schemas.typings.platform.strings import ListItemKey
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

INPUT_TOKENS_FIELD: DocumentFieldPath = DocumentFieldPath("input_tokens")
OUTPUT_TOKENS_FIELD: DocumentFieldPath = DocumentFieldPath("output_tokens")
COST_FIELD: DocumentFieldPath = DocumentFieldPath("cost_micro_usd")
TOOL_ERRORS_FIELD: DocumentFieldPath = DocumentFieldPath("tool_calls[].is_error")
LIST_BATCH: KeysetReadLimit = KeysetReadLimit(1_000)
# Messages someone wrote (system notes of the voice agent are not previews).
WRITTEN_AUTHORS: tuple[MessageAuthor, ...] = (
    MessageAuthor.CUSTOMER,
    MessageAuthor.ASSISTANT,
    MessageAuthor.STAFF,
)


class MessageListing(BusinessScopedRepository[MessageDocument]):
    """Pages of a transcript and the counts and sums the database computes."""

    def page_transcript(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        window: KeysetSlice,
    ) -> list[MessageDocument]:
        """Messages of the conversation newest first."""

        return self._page_in_business(
            business_id,
            (CREATED_AT_FIELD,),
            window,
            DocumentFilter(
                matches=(field_equals(CONVERSATION_ID_FIELD, conversation_id),)
            ),
        )

    def list_by_conversations(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> list[MessageDocument]:
        """Oldest first, read in keyset batches of `LIST_BATCH` messages."""

        if not conversation_ids:
            return []

        found: list[MessageDocument] = []
        window = KeysetSlice(limit=LIST_BATCH)
        while True:
            batch: list[MessageDocument] = self._page_in_business(
                business_id,
                (CREATED_AT_FIELD,),
                window,
                DocumentFilter(
                    among=(field_among(CONVERSATION_ID_FIELD, conversation_ids),)
                ),
                is_descending=False,
            )
            found.extend(batch)
            if len(batch) < int(LIST_BATCH):
                return found

            last: MessageDocument = batch[-1]
            window = KeysetSlice(
                after=KeysetPosition(
                    sort_values=(ListSortValue(int(last.created_at)),),
                    item_key=ListItemKey(str(last.id)),
                ),
                limit=LIST_BATCH,
            )

    def tally_conversations(
        self,
        business_id: BusinessId,
        conversation_ids: Sequence[ConversationId],
    ) -> dict[ConversationId, ConversationMessageTally]:
        """Message counts (all, the customer's) of each conversation."""

        if not conversation_ids:
            return {}

        totals: dict[ConversationId, int] = {}
        customer: dict[ConversationId, int] = {}
        for group in self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    among=(field_among(CONVERSATION_ID_FIELD, conversation_ids),)
                ),
                group_by=(CONVERSATION_ID_FIELD, AUTHOR_FIELD),
            ),
        ):
            conversation_id = ConversationId(str(group.values[0]))
            totals[conversation_id] = totals.get(conversation_id, 0) + int(group.count)
            if parse_choice(MessageAuthor, group.values[1]) is MessageAuthor.CUSTOMER:
                customer[conversation_id] = int(group.count)

        return {
            conversation_id: ConversationMessageTally(
                message_count=ConversationMessageCount(total),
                customer_message_count=ConversationMessageCount(
                    customer.get(conversation_id, 0)
                ),
            )
            for conversation_id, total in totals.items()
        }

    def find_latest_written(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> MessageDocument | None:
        """The newest message a person or the assistant wrote."""

        found: list[MessageDocument] = self._page_in_business(
            business_id,
            (CREATED_AT_FIELD,),
            KeysetSlice(limit=KeysetReadLimit(1)),
            DocumentFilter(
                matches=(field_equals(CONVERSATION_ID_FIELD, conversation_id),),
                among=(field_among(AUTHOR_FIELD, WRITTEN_AUTHORS),),
            ),
        )
        return found[0] if found else None

    def sum_usage(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
    ) -> ConversationUsageView:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(field_equals(CONVERSATION_ID_FIELD, conversation_id),)
                ),
                totals_of=(INPUT_TOKENS_FIELD, OUTPUT_TOKENS_FIELD, COST_FIELD),
            ),
        )
        if not groups or len(groups[0].totals) != 3:
            return ConversationUsageView()

        input_tokens, output_tokens, cost = groups[0].totals
        return ConversationUsageView(
            input_tokens=LlmTokenCount(int(input_tokens)),
            output_tokens=LlmTokenCount(int(output_tokens)),
            cost_micro_usd=CostMicroUsd(int(cost)),
        )

    def count_customer_messages(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
        conversation_ids: Sequence[ConversationId] | None = None,
    ) -> PeriodItemCount:
        """Customer messages written in the period (of these conversations)."""

        among: tuple[DocumentFieldAmong, ...] = (
            ()
            if conversation_ids is None
            else (field_among(CONVERSATION_ID_FIELD, conversation_ids),)
        )
        return period_count(
            self._aggregate_in_business(
                business_id,
                DocumentAggregation(
                    where=DocumentFilter(
                        matches=(field_equals(AUTHOR_FIELD, MessageAuthor.CUSTOMER),),
                        among=among,
                        ranges=(time_range(CREATED_AT_FIELD, start, end),),
                    )
                ),
            )
        )

    def sum_cost_by_conversation(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
    ) -> dict[ConversationId, CostMicroUsd]:
        """Model spend recorded on the messages of the period, per conversation."""

        return {
            ConversationId(str(group.values[0])): CostMicroUsd(int(group.totals[0]))
            for group in self._aggregate_in_business(
                business_id,
                DocumentAggregation(
                    where=DocumentFilter(
                        ranges=(time_range(CREATED_AT_FIELD, start, end),)
                    ),
                    group_by=(CONVERSATION_ID_FIELD,),
                    totals_of=(COST_FIELD,),
                ),
            )
            if group.values[0] is not None
        }

    def list_with_tool_errors(
        self,
        business_id: BusinessId,
        since: Microseconds,
    ) -> list[MessageDocument]:
        """Messages from `since` on with at least one failed tool call."""

        return self._list_in_range(
            business_id,
            time_range(CREATED_AT_FIELD, starting_at=since),
            [field_equals(TOOL_ERRORS_FIELD, True)],
        )
