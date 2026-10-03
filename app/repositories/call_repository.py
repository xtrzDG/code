"""The calls of a business: one document per phone call (voice channel)."""

from app.contracts.repositories.conversation_repositories import CallRepoContract
from app.repositories.conversation_lookup_fields import PROVIDER_CALL_ID_FIELD
from app.repositories.document_queries import field_equals
from app.repositories.listing.contact_listing import CallListing
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.call_recordings import CallRecordingMove
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import CallId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.utilities.recordings.recording_moves import recording_moved


class CallRepository(CallListing, CallRepoContract):
    def save(self, call: CallDocument) -> None:
        self._store(str(call.id), call)

    def get(self, business_id: BusinessId, call_id: CallId) -> CallDocument | None:
        return self._load(business_id, str(call_id))

    def find_by_provider_call_id(
        self,
        business_id: BusinessId,
        provider_call_id: ProviderCallId,
    ) -> CallDocument | None:
        return self._find_in_business(
            business_id, [field_equals(PROVIDER_CALL_ID_FIELD, provider_call_id)]
        )

    def list_by_business(self, business_id: BusinessId) -> list[CallDocument]:
        return sorted(
            self._list_in_business(business_id),
            key=lambda call: call.started_at,
            reverse=True,
        )

    def move_recording(
        self, business_id: BusinessId, call_id: CallId, moved: CallRecordingMove
    ) -> bool:
        change = recording_moved(moved)
        return self._modify_in_business(business_id, str(call_id), change) is not None
