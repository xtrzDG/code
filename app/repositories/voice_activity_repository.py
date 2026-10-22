from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.monitoring import VoiceActivityRepoContract
from app.repositories.document_queries import CREATED_AT_FIELD, field_equals, time_range
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

CHANNEL_FIELD: DocumentFieldPath = DocumentFieldPath("channel")


class VoiceActivityRepository(VoiceActivityRepoContract):
    """
    The voice platform's finished-call reports as the inbox accepted them:
    the inbox events of the phone channel (only the post-call webhook
    stores them), counted by the database over the platform-wide arrival
    index `inbound_events_doc_created_at_idx` (1020). The inbox keeps
    events 30 days, enough for the week before.
    """

    def __init__(
        self,
        inbound_event_collection: DocumentCollectionAdapterContract[
            InboundEventDocument
        ],
    ) -> None:
        self._events: DocumentCollectionAdapterContract[InboundEventDocument] = (
            inbound_event_collection
        )

    def count_post_call_reports(self, window: ActivityWindow) -> DocumentCount:
        return self._events.count_by_fields(
            [field_equals(CHANNEL_FIELD, ChannelKind.PHONE)],
            within=time_range(
                CREATED_AT_FIELD, starting_at=window.since, ending_before=window.until
            ),
        )
