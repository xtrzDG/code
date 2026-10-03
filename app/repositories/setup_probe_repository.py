from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.setup_repositories import SetupProbeRepoContract
from app.repositories.activation_probe_repository import PROBE_LIMIT
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    IS_SANDBOX_FIELD,
    field_equals,
    of_business,
    time_range,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

CHANNEL_USER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("channel_user_id")
# A sender writes a handful of conversations at most before the probe sees
# them; a window holds few conversations of a business that just went live.
SENDER_PROBE_LIMIT: DocumentQueryLimit = DocumentQueryLimit(5)
WINDOW_PROBE_LIMIT: DocumentQueryLimit = DocumentQueryLimit(20)


class SetupProbeRepository(SetupProbeRepoContract):
    """
    Finds what the guide after the launch waits for, skipping the test
    chat and the automatic checks: a conversation from one of the owner's
    own phones or chats (one indexed lookup per sender), the first one in a
    time window (an index range scan), and the first booking made in a
    conversation after hours (the business's earliest bookings through the
    business index, their conversations in one read).
    """

    def __init__(
        self,
        conversation_collection: DocumentCollectionAdapterContract[
            ConversationDocument
        ],
        booking_collection: DocumentCollectionAdapterContract[BookingDocument],
    ) -> None:
        self._conversation_collection: DocumentCollectionAdapterContract[
            ConversationDocument
        ] = conversation_collection
        self._booking_collection: DocumentCollectionAdapterContract[BookingDocument] = (
            booking_collection
        )

    def find_first_conversation_from(
        self,
        business_id: BusinessId,
        channel_user_ids: frozenset[ChannelUserId],
    ) -> Microseconds | None:
        found: list[ConversationDocument] = []
        for channel_user_id in sorted(channel_user_ids):
            found.extend(
                self._conversation_collection.list_by_fields(
                    [
                        of_business(business_id),
                        field_equals(CHANNEL_USER_ID_FIELD, channel_user_id),
                        field_equals(IS_SANDBOX_FIELD, False),
                    ],
                    limit=SENDER_PROBE_LIMIT,
                )
            )

        return earliest_real(found)

    def find_first_conversation_between(
        self,
        business_id: BusinessId,
        since: Microseconds,
        until: Microseconds,
    ) -> Microseconds | None:
        return earliest_real(
            self._conversation_collection.list_by_range(
                time_range(CREATED_AT_FIELD, since, until),
                [of_business(business_id), field_equals(IS_SANDBOX_FIELD, False)],
                limit=WINDOW_PROBE_LIMIT,
            )
        )

    def find_first_after_hours_booking_at(
        self, business_id: BusinessId
    ) -> Microseconds | None:
        bookings: list[BookingDocument] = [
            booking
            for booking in self._booking_collection.list_by_fields(
                [of_business(business_id), field_equals(IS_SANDBOX_FIELD, False)],
                limit=PROBE_LIMIT,
            )
            if booking.conversation_id is not None
        ]
        if bookings == []:
            return None

        after_hours: set[str] = {
            str(conversation.id)
            for conversation in self._conversation_collection.get_many(
                sorted({str(booking.conversation_id) for booking in bookings})
            )
            if conversation.business_id == business_id and conversation.is_after_hours
        }
        return min(
            (
                booking.created_at
                for booking in bookings
                if str(booking.conversation_id) in after_hours
            ),
            default=None,
        )


def earliest_real(conversations: Sequence[ConversationDocument]) -> Microseconds | None:
    """When the earliest conversation with a real customer channel began."""

    return min(
        (
            conversation.created_at
            for conversation in conversations
            if not conversation.is_sandbox
            and conversation.channel is not ChannelKind.OWNER_TEST
        ),
        default=None,
    )
