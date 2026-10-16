from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.monitoring import PlatformActivityRepoContract
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    field_equals,
    time_range,
    without_sandbox,
)
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.platform_health import ActivityWindow, OutboundTally
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
TOOL_ERRORS_FIELD: DocumentFieldPath = DocumentFieldPath("tool_calls[].is_error")


class PlatformActivityRepository(PlatformActivityRepoContract):
    """
    What the platform did in a window, counted by the database across every
    business: handoffs by their platform-wide created_at index (1093), the
    outbox by its created_at index (1020) grouped by state, and messages
    with a failed tool call by the lookup keys of `tool_calls[].is_error`.
    """

    def __init__(
        self,
        handoff_collection: DocumentCollectionAdapterContract[HandoffDocument],
        outbound_collection: DocumentCollectionAdapterContract[OutboundMessageDocument],
        message_collection: DocumentCollectionAdapterContract[MessageDocument],
    ) -> None:
        self._handoffs: DocumentCollectionAdapterContract[HandoffDocument] = (
            handoff_collection
        )
        self._outbound: DocumentCollectionAdapterContract[OutboundMessageDocument] = (
            outbound_collection
        )
        self._messages: DocumentCollectionAdapterContract[MessageDocument] = (
            message_collection
        )

    def count_handoffs(self, window: ActivityWindow) -> DocumentCount:
        groups: list[DocumentGroupCount] = self._handoffs.count_by(
            DocumentAggregation(
                where=DocumentFilter(
                    ranges=(created_within(window),),
                    excluding=(without_sandbox(),),
                )
            )
        )
        return DocumentCount(sum(int(group.count) for group in groups))

    def count_outbound(self, window: ActivityWindow) -> list[OutboundTally]:
        groups: list[DocumentGroupCount] = self._outbound.count_by(
            DocumentAggregation(
                where=DocumentFilter(ranges=(created_within(window),)),
                group_by=(STATUS_FIELD,),
            )
        )
        return [
            OutboundTally(
                status=OutboundMessageStatus(str(status)),
                count=DocumentCount(int(group.count)),
            )
            for group in groups
            for status in group.values
            if status is not None
        ]

    def count_tool_error_messages(self, window: ActivityWindow) -> DocumentCount:
        return self._messages.count_by_fields(
            [field_equals(TOOL_ERRORS_FIELD, True)],
            within=created_within(window),
        )


def created_within(window: ActivityWindow) -> DocumentFieldRange:
    return time_range(
        CREATED_AT_FIELD, starting_at=window.since, ending_before=window.until
    )
