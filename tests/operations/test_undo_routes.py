"""The Undo routes: revert-status of a booking and reopen of a handoff."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.handoffs import HandoffCommand
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.operations.operations_api import STRANGER_TOKEN, Api


def test_undo_of_arrived_restores_the_booking_and_explains_refusals() -> None:
    api = Api()
    created = api.send(
        "POST",
        "/bookings",
        {
            "contact_name": "Levan",
            "date": "2026-10-05",
            "time": "19:00",
            "party_size": 2,
            "source_channel": "phone",
        },
    )
    booking_id = created.json()["booking"]["id"]
    path = f"/bookings/{booking_id}/revert-status"

    api.send("PATCH", f"/bookings/{booking_id}", {"status": "completed"})
    restored = api.send("POST", path, {"status": "completed"})
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "confirmed"

    again = api.send("POST", path, {"status": "completed"})
    assert again.status_code == 409
    assert again.json()["reasons"][0]["code"] == "nothing_to_undo"

    api.send("POST", f"/bookings/{booking_id}/cancel")
    taken = api.send(
        "POST",
        "/bookings",
        {
            "contact_name": "Walk-in",
            "date": "2026-10-05",
            "time": "19:00",
            "party_size": 2,
            "source_channel": "phone",
        },
    )
    assert taken.status_code == 201
    refused = api.send("POST", path, {"status": "cancelled"})
    assert refused.status_code == 409
    assert refused.json()["reasons"][0]["code"] == "slot_taken"

    assert api.send("POST", path, {}).status_code == 422
    assert api.send("POST", path, {"status": "gone"}).status_code == 422
    assert (
        api.send(
            "POST", "/bookings/booking_nope/revert-status", {"status": "completed"}
        )
    ).status_code == 404
    stranger = api.send("POST", path, {"status": "cancelled"}, token=STRANGER_TOKEN)
    assert stranger.status_code == 404


def test_undo_of_resolve_reopens_the_handoff() -> None:
    api = Api()
    conversation = api.world.add_conversation(
        api.business, api.contact, ChannelKind.TELEGRAM, language="ka"
    )
    handoff = api.world.handoff_to_human().run(
        HandoffCommand(
            business_id=api.business.id,
            conversation_id=conversation.id,
            contact_id=api.contact.id,
            reason=HandoffReason.CUSTOMER_REQUEST,
            summary=HandoffSummary("Wants to talk about a banquet."),
            urgency=HandoffUrgency.NORMAL,
            source_channel=ChannelKind.TELEGRAM,
            language=LanguageTag("ka"),
        )
    )

    resolved = api.send("POST", f"/handoffs/{handoff.id}/resolve")
    assert resolved.json()["status"] == "resolved"
    reopened = api.send("POST", f"/handoffs/{handoff.id}/reopen")
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "pending"
    assert reopened.json()["resolved_at"] is None
    assert [
        item["id"] for item in api.get("/handoffs", is_open="true").json()["items"]
    ] == [str(handoff.id)]
    assert api.send("POST", "/handoffs/handoff_nope/reopen").status_code == 404
