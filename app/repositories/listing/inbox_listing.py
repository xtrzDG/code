"""The views of the team inbox over the conversations, and their counts."""

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    LAST_MESSAGE_AT_FIELD,
    STATUS_FIELD,
)
from app.repositories.document_queries import field_equals, without_sandbox
from app.repositories.listing.conversation_listing import CHANNEL_FIELD
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.inbox import InboxView
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.inbox_views import InboxViewCounts, InboxViewFilter
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.inbox.constrained_integers import AwaitingConversationCount
from app.schemas.typings.platform.constrained_integers import ListItemCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId

HAS_OPEN_REQUEST_FIELD: DocumentFieldPath = DocumentFieldPath("has_open_request")
AWAITS_TEAM_FIELD: DocumentFieldPath = DocumentFieldPath("awaits_team")
ASSIGNEE_FIELD: DocumentFieldPath = DocumentFieldPath("assignee_user_id")
TRUE_TEXT: str = "true"
HANDOFF_TEXT: str = ConversationStatus.HANDOFF.value


class InboxListing(BusinessScopedRepository[ConversationDocument]):
    """
    Each view is one keyset page on an index of the business that starts
    with its condition and ends with `last_message_at` (migration 1053);
    the counts are one grouped count of the conversations waiting for the
    team, which are few.
    """

    def page_inbox(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        view: InboxViewFilter,
    ) -> list[ConversationDocument]:
        matches: list[DocumentFieldMatch] = []
        missing: tuple[DocumentFieldPath, ...] = ()
        if view.view is InboxView.NEEDS_PERSON:
            matches.append(field_equals(STATUS_FIELD, ConversationStatus.HANDOFF))
        elif view.view is InboxView.REQUESTS:
            matches.append(field_equals(HAS_OPEN_REQUEST_FIELD, True))
        elif view.view is InboxView.MINE:
            matches.append(field_equals(AWAITS_TEAM_FIELD, True))
            matches.append(field_equals(ASSIGNEE_FIELD, view.viewer))
        elif view.view is InboxView.UNASSIGNED:
            matches.append(field_equals(AWAITS_TEAM_FIELD, True))
            missing = (ASSIGNEE_FIELD,)

        if view.channel is not None:
            matches.append(field_equals(CHANNEL_FIELD, view.channel))

        return self._page_in_business(
            business_id,
            (LAST_MESSAGE_AT_FIELD,),
            window,
            DocumentFilter(
                matches=tuple(matches),
                excluding=(without_sandbox(),),
                missing=missing,
            ),
        )

    def count_inbox(self, business_id: BusinessId, viewer: UserId) -> InboxViewCounts:
        needs_person = requests = mine = unassigned = 0
        for group in self._awaiting_groups(
            business_id, (STATUS_FIELD, HAS_OPEN_REQUEST_FIELD, ASSIGNEE_FIELD)
        ):
            status, open_request, assignee = group.values
            count: int = int(group.count)
            if status is not None and str(status) == HANDOFF_TEXT:
                needs_person += count

            if open_request is not None and str(open_request) == TRUE_TEXT:
                requests += count

            if assignee is None:
                unassigned += count
            elif str(assignee) == str(viewer):
                mine += count

        return InboxViewCounts(
            needs_person=ListItemCount(needs_person),
            requests=ListItemCount(requests),
            mine=ListItemCount(mine),
            unassigned=ListItemCount(unassigned),
        )

    def count_awaiting_by_assignee(
        self, business_id: BusinessId
    ) -> dict[UserId, AwaitingConversationCount]:
        return {
            UserId(str(assignee)): AwaitingConversationCount(int(group.count))
            for group in self._awaiting_groups(business_id, (ASSIGNEE_FIELD,))
            if (assignee := group.values[0]) is not None
        }

    def _awaiting_groups(
        self,
        business_id: BusinessId,
        group_by: tuple[DocumentFieldPath, ...],
    ) -> list[DocumentGroupCount]:
        return self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(
                    matches=(field_equals(AWAITS_TEAM_FIELD, True),),
                    excluding=(without_sandbox(),),
                ),
                group_by=group_by,
            ),
        )
