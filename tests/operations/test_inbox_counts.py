"""The inbox counts behind the badges on Messages: what counts, who may read them."""

import pytest

from app.schemas.constants.bookings import LeadStatus, LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffStatus, HandoffUrgency
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.operations.inbox_counts import InboxCountsQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.strings import HandoffSummary
from tests.operations.operations_api import (
    OWNER_TOKEN,
    STAFF_TOKEN,
    STRANGER_TOKEN,
    Api,
)


def add_handoff(api: Api, status: HandoffStatus, is_sandbox: bool = False) -> None:
    conversation = api.world.add_conversation(
        api.business, api.contact, ChannelKind.WHATSAPP
    )
    api.world.handoff_repo.save(
        HandoffDocument(
            business_id=api.business.id,
            conversation_id=conversation.id,
            contact_id=api.contact.id,
            reason=HandoffReason.CUSTOMER_REQUEST,
            summary=HandoffSummary("Wants to talk to the manager"),
            urgency=HandoffUrgency.NORMAL,
            status=status,
            is_sandbox=is_sandbox,
        )
    )


def add_lead(api: Api, status: LeadStatus, is_sandbox: bool = False) -> None:
    api.world.lead_repo.save(
        LeadDocument(
            business_id=api.business.id,
            contact_id=api.contact.id,
            lead_type=LeadType.BANQUET,
            details=LeadDetails("A birthday for 30 guests"),
            source_channel=ChannelKind.WHATSAPP,
            status=status,
            is_sandbox=is_sandbox,
        )
    )


def test_counts_open_handoffs_and_new_requests_without_test_activity() -> None:
    api = Api()
    for status in (
        HandoffStatus.PENDING,
        HandoffStatus.NOTIFIED,
        HandoffStatus.NOTIFICATION_FAILED,
    ):
        add_handoff(api, status)
    add_handoff(api, HandoffStatus.RESOLVED)
    add_handoff(api, HandoffStatus.PENDING, is_sandbox=True)
    add_lead(api, LeadStatus.NEW)
    add_lead(api, LeadStatus.IN_PROGRESS)
    add_lead(api, LeadStatus.WON)
    add_lead(api, LeadStatus.NEW, is_sandbox=True)

    counts = api.world.inbox_counts().run(InboxCountsQuery(business_id=api.business.id))

    assert counts.business_id == api.business.id
    assert counts.open_handoff_count == 3
    assert counts.new_lead_count == 1


def test_an_empty_inbox_counts_zero() -> None:
    api = Api()

    response = api.get("/inbox-counts")

    assert response.status_code == 200
    assert response.json() == {
        "business_id": str(api.business.id),
        "open_handoff_count": 0,
        "new_lead_count": 0,
    }


def test_owners_and_staff_read_the_counts_without_an_audit_entry() -> None:
    api = Api()
    add_handoff(api, HandoffStatus.PENDING)
    add_lead(api, LeadStatus.NEW)
    audited_before = len(api.world.audit_repo.list_by_business(api.business.id))

    for token in (OWNER_TOKEN, STAFF_TOKEN):
        response = api.get("/inbox-counts", token=token)
        assert response.status_code == 200
        assert response.json()["open_handoff_count"] == 1
        assert response.json()["new_lead_count"] == 1

    # Counts are not a view of anyone's personal data: polling them records nothing.
    assert len(api.world.audit_repo.list_by_business(api.business.id)) == audited_before


def test_others_cannot_read_the_counts() -> None:
    api = Api()

    assert api.client.get(api.url("/inbox-counts")).status_code == 401
    stranger = api.get("/inbox-counts", token=STRANGER_TOKEN)
    assert stranger.status_code == 404
    assert stranger.json()["error"] == "not_found"


def test_an_unknown_business_is_not_found() -> None:
    api = Api()

    with pytest.raises(NotFoundError):
        api.world.inbox_counts().run(InboxCountsQuery(business_id=BusinessId()))
