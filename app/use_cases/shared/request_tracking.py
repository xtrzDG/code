"""
What a request (lead) changes in the team inbox: whether its conversation
has an open request and, for a new one, an automatic assignment. Neither
step ever fails the request itself: the lead is stored and staff notified
first, and a failed step is logged (the next change of a request of the
conversation recounts).
"""

import logging

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.inbox import InboxView
from app.schemas.domain.bookings import LeadDocument
from app.schemas.dto.inbox.assignment import (
    AutoAssignCommand,
    AutoAssignResult,
    OpenRequestRefresh,
    OpenRequestState,
)
from app.schemas.exceptions.base_exception import ApplicationError

LOGGER: logging.Logger = logging.getLogger(__name__)


def track_request(
    lead: LeadDocument,
    refresh_open_request: UseCaseContract[OpenRequestRefresh, OpenRequestState],
    auto_assign: UseCaseContract[AutoAssignCommand, AutoAssignResult] | None = None,
) -> None:
    """
    Recount the open requests of the lead's conversation; for a new lead
    (`auto_assign` given) let the inbox assign the conversation too.
    """

    if lead.conversation_id is None:
        return

    try:
        refresh_open_request.run(
            OpenRequestRefresh(
                business_id=lead.business_id, conversation_id=lead.conversation_id
            )
        )
        if auto_assign is not None:
            auto_assign.run(
                AutoAssignCommand(
                    business_id=lead.business_id,
                    conversation_id=lead.conversation_id,
                    trigger=InboxView.REQUESTS,
                    is_sandbox=lead.is_sandbox,
                )
            )
    except ApplicationError:
        LOGGER.exception("The inbox could not take request %s into account.", lead.id)
