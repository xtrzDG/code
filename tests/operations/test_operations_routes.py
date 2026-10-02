"""Operations routes: login and tenants, OpenAPI, availability, leads and dashboard."""

from app.clients.google.google_calendar_redirect import GOOGLE_CALENDAR_CALLBACK_PATH
from app.gateways.http.operations.google_calendar_routes import (
    GOOGLE_CALENDAR_COMPLETE_PATH as COMPLETE_PATH,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.handoffs import HandoffCommand, RecordUnansweredQuestionCommand
from app.schemas.typings.handoffs.strings import HandoffSummary, UnansweredQuestionText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.operations.operations_api import (
    OWNER_TOKEN,
    STAFF_TOKEN,
    STRANGER_TOKEN,
    Api,
)


def test_authentication_and_tenant_isolation() -> None:
    api = Api()

    assert api.client.get(api.url("/bookings")).status_code == 401
    assert api.get("/bookings", token="unknown").status_code == 401
    response = api.get("/bookings", token=STRANGER_TOKEN)
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
    assert (
        api.client.get(
            "/v1/businesses/not-an-id/bookings",
            headers={"Authorization": f"Bearer {STAFF_TOKEN}"},
        ).status_code
        == 404
    )


def test_openapi_schema_lists_every_route() -> None:
    api = Api()

    paths = set(api.application.openapi()["paths"])

    assert len(paths) == 16
    assert "/v1/businesses/{business_id}/bookings/{booking_id}/reschedule" in paths
    assert GOOGLE_CALENDAR_CALLBACK_PATH in paths
    assert COMPLETE_PATH in paths


def test_openapi_schema_describes_every_json_body() -> None:
    api = Api()
    paths = api.application.openapi()["paths"]
    prefix = "/v1/businesses/{business_id}"

    bodies = {
        (f"{prefix}/bookings", "post"): "contact_name",
        (f"{prefix}/bookings/{{booking_id}}/reschedule", "post"): "new_date",
        (f"{prefix}/bookings/{{booking_id}}", "patch"): "party_size",
        (f"{prefix}/leads/{{lead_id}}", "patch"): "status",
        (f"{prefix}/unanswered-questions/{{question_id}}/answer", "post"): "answer",
    }
    for (path, method), field in bodies.items():
        schema = paths[path][method]["requestBody"]["content"]["application/json"]
        assert field in schema["schema"]["properties"], (path, method)


def test_availability_query_parameters_are_typed() -> None:
    api = Api()

    response = api.get("/availability", date="2026-10-06", time="19:00", party_size="3")

    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "Asia/Tbilisi"
    assert [slot["time"] for slot in body["slots"]] == [
        "18:00",
        "18:30",
        "19:00",
        "19:30",
        "20:00",
    ]
    assert body["slots"][0]["booking_unit"] == "time_slot"
    for params in (
        {"date": "2026-13-01"},
        {"date": "2026-10-06", "party_size": "three"},
        {"date": "2026-10-06", "resource_kind": "spaceship"},
        {"date": "2026-10-06", "party_size": "0"},
        {"date": "0001-01-01"},
        {"date": "9999-12-31"},
    ):
        bad = api.get("/availability", **params)
        assert bad.status_code == 422, params
        assert bad.json()["error"] == "validation_failed"

    assert api.get("/availability").status_code == 422
    full_day = api.get("/availability", date="2026-10-06", full_day="true").json()
    assert len(full_day["slots"]) > 10
    assert api.get("/availability", date="2026-10-06", full_day="x").status_code == 422


def test_leads_handoffs_and_questions() -> None:
    api = Api()
    conversation = api.world.add_conversation(api.business, api.contact)
    handoff = api.world.handoff_to_human().run(
        HandoffCommand(
            business_id=api.business.id,
            conversation_id=conversation.id,
            contact_id=api.contact.id,
            reason=HandoffReason.COMPLAINT,
            summary=HandoffSummary("Cold soup"),
            urgency=HandoffUrgency.HIGH,
            source_channel=ChannelKind.WHATSAPP,
            language=LanguageTag("ka"),
        )
    )
    question = api.world.record_unanswered_question().run(
        RecordUnansweredQuestionCommand(
            business_id=api.business.id,
            question=UnansweredQuestionText("Do you have a kids menu?"),
            language=LanguageTag("en"),
        )
    )

    leads = api.get("/leads").json()
    assert leads["items"] == []
    assert leads["next_cursor"] is None
    assert {count["status"]: count["count"] for count in leads["status_counts"]} == {
        "new": 0,
        "in_progress": 0,
        "won": 0,
        "lost": 0,
    }
    assert api.get("/leads", status="won").status_code == 200
    handoffs = api.get("/handoffs", status="pending").json()["items"]
    assert [item["id"] for item in handoffs] == [str(handoff.id)]
    waiting = api.get("/handoffs", is_open="true").json()
    assert (waiting["open_count"], waiting["resolved_count"]) == (1, 0)
    resolved = api.send("POST", f"/handoffs/{handoff.id}/resolve")
    assert resolved.json()["status"] == "resolved"
    assert api.get("/handoffs", is_open="true").json()["items"] == []
    assert len(api.get("/handoffs", is_open="false").json()["items"]) == 1
    assert api.get("/handoffs", is_open="maybe").status_code == 422

    questions = api.get("/unanswered-questions").json()["items"]
    assert questions[0]["question"] == "Do you have a kids menu?"
    answer = {"answer": "Yes, with five dishes."}
    staff_answer = api.send(
        "POST", f"/unanswered-questions/{question.id}/answer", answer
    )
    assert staff_answer.status_code == 403
    owner_answer = api.send(
        "POST", f"/unanswered-questions/{question.id}/answer", answer, OWNER_TOKEN
    )
    assert owner_answer.status_code == 200
    assert owner_answer.json()["requires_reassembly"] is True
    assert api.get("/unanswered-questions").json()["items"] == []
    assert (
        len(api.get("/unanswered-questions", include_resolved="true").json()["items"])
        == 1
    )
    assert api.get("/unanswered-questions", include_resolved="maybe").status_code == 422


def test_dashboard_route() -> None:
    api = Api()

    response = api.get("/dashboard", **{"from": "2026-10-01", "to": "2026-10-05"})
    default = api.get("/dashboard")

    assert response.status_code == 200
    assert response.json()["date_from"] == "2026-10-01"
    assert response.json()["conversation_count"] == 0
    assert len(response.json()["daily"]) == 5
    assert response.json()["package"] is None
    assert default.json()["date_to"] == "2026-10-05"
    assert (
        api.get("/dashboard", **{"from": "2026-10-05", "to": "2026-10-01"}).status_code
        == 422
    )
    assert api.get("/dashboard", to="9999-12-31").status_code == 422
    assert api.get("/dashboard", **{"from": "0001-01-01"}).status_code == 422
