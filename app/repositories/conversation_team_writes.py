"""
Writes of a conversation that respect its team inbox fields: a plain save
keeps them as stored, an assignment is a compare-and-set on its revision,
and the open-request flag has its own write.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.assignment import ConversationAssignmentChange
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.inbox.booleans import HasOpenRequest
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from app.utilities.inbox.team_fields import keep_team_fields, with_team_attention


class ConversationTeamWrites(BusinessScopedRepository[ConversationDocument]):
    """The writes of `ConversationRepository` that touch the team fields."""

    def _save_keeping_team_fields(self, conversation: ConversationDocument) -> None:
        """
        Overwrite the stored conversation except its team fields, in one
        step (a row lock on Postgres); a new conversation is inserted as
        given. A concurrent first save of the same conversation makes the
        insert lose, and the write then merges into what it stored.
        """

        key: str = str(conversation.id)

        def merge(stored: ConversationDocument) -> ConversationDocument:
            return keep_team_fields(conversation, stored)

        if self._modify_in_business(conversation.business_id, key, merge) is not None:
            return

        if self._collection.insert_if_absent(key, with_team_attention(conversation)):
            return

        self._modify_in_business(conversation.business_id, key, merge)

    def _save_many_as_given(
        self, conversations: Sequence[ConversationDocument]
    ) -> None:
        """Bulk loads write the team fields as given (awaits_team derived)."""

        self._store_many(
            [
                (str(conversation.id), with_team_attention(conversation))
                for conversation in conversations
            ]
        )

    def assign(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        change: ConversationAssignmentChange,
    ) -> ConversationDocument | None:
        def compare_and_set(
            stored: ConversationDocument,
        ) -> ConversationDocument | None:
            if stored.assignment_revision != change.expected_revision:
                return None

            is_assigned: bool = change.assignee_user_id is not None
            return with_team_attention(
                stored.model_copy(
                    update={
                        "assignee_user_id": change.assignee_user_id,
                        "assigned_by": change.assigned_by if is_assigned else None,
                        "assigned_at": change.at if is_assigned else None,
                        "assignment_revision": AssignmentRevision(
                            int(stored.assignment_revision) + 1
                        ),
                        "updated_at": change.at,
                    }
                )
            )

        return self._modify_in_business(
            business_id, str(conversation_id), compare_and_set
        )

    def set_open_request(
        self,
        business_id: BusinessId,
        conversation_id: ConversationId,
        has_open_request: HasOpenRequest,
        at: Microseconds,
    ) -> ConversationDocument | None:
        def mark(stored: ConversationDocument) -> ConversationDocument | None:
            if stored.has_open_request == has_open_request:
                return None

            return with_team_attention(
                stored.model_copy(
                    update={"has_open_request": has_open_request, "updated_at": at}
                )
            )

        changed: ConversationDocument | None = self._modify_in_business(
            business_id, str(conversation_id), mark
        )
        return changed or self._load(business_id, str(conversation_id))
