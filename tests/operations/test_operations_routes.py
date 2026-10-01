from collections.abc import Mapping
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.clients.google.google_calendar_client import GOOGLE_CALENDAR_CALLBACK_PATH
from app.contracts.operator_contract import OperatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.operations_routes import (
    GOOGLE_CALENDAR_CALLBACK_PATH as ROUTE_CALLBACK_PATH,
)
from app.gateways.http.operations_routes import build_operations_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.calendar_repositories import (
    CalendarAuthorizationStateRepository,
    CalendarConnectionRepository,
    CalendarEventLinkRepository,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.dto.handoffs import HandoffCommand, RecordUnansweredQuestionCommand
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.handoffs.strings import (
    HandoffSummary,
    UnansweredQuestionText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.calendar.complete_google_calendar_connection_use_case import (
    CompleteGoogleCalendarConnectionUseCase,
)
from app.use_cases.calendar.disconnect_google_calendar_use_case import (
    DisconnectGoogleCalendarUseCase,
)
from app.use_cases.calendar.start_google_calendar_connection_use_case import (
    StartGoogleCalendarConnectionUseCase,
)
from tests.operations.builders import OperationsWorld
from tests.operations.fake_google import FakeGoogle
from tests.operations.fakes import ReversingSecretCipher

OWNER_TOKEN: str = "owner-token"
STAFF_TOKEN: str = "staff-token"
STRANGER_TOKEN: str = "stranger-token"


def operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> OperatorContract[InputData, OutputData]:
    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))


class TokenAuthenticator(OperatorContract[AccessToken, UserId]):
    def __init__(self, users: dict[str, UserId]) -> None:
        self._users: dict[str, UserId] = users

    def operate(self, input_data: AccessToken) -> UserId:
        user_id: UserId | None = self._users.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return user_id


class Api:
    """The operations router over an in-memory Tbilisi restaurant."""

    def __init__(self) -> None:
        self.world = OperationsWorld()
        self.owner_id, self.staff_id = UserId(), UserId()
        self.business = self.world.add_business(
            owner_id=self.owner_id, staff_ids=(self.staff_id,)
        )
        self.world.add_profile(self.business)
        self.world.add_resource(self.business, "Table 4", capacity=4)
        self.contact = self.world.add_contact(self.business, "Nino", "+995555123456")
        self.google = FakeGoogle()
        google_client = self.google.client()
        cipher = ReversingSecretCipher()
        state_repo = CalendarAuthorizationStateRepository(
            InMemoryDocumentCollectionAdapter[CalendarAuthorizationStateDocument](
                CalendarAuthorizationStateDocument
            )
        )
        self.connection_repo = CalendarConnectionRepository(
            InMemoryDocumentCollectionAdapter[CalendarConnectionDocument](
                CalendarConnectionDocument
            )
        )
        link_repo = CalendarEventLinkRepository(
            InMemoryDocumentCollectionAdapter[CalendarEventLinkDocument](
                CalendarEventLinkDocument
            )
        )
        world = self.world
        application = FastAPI()
        install_error_handlers(application)
        application.include_router(
            build_operations_router(
                current_user=build_current_user_dependency(
                    TokenAuthenticator(
                        {
                            OWNER_TOKEN: self.owner_id,
                            STAFF_TOKEN: self.staff_id,
                            STRANGER_TOKEN: UserId(),
                        }
                    )
                ),
                authorize_business_access=operator(
                    AuthorizeBusinessAccessUseCase(
                        business_repo=world.business_repo,
                        user_repo=world.user_repo,
                        audit_log_repo=world.audit_repo,
                        wall_clock=world.clock.wall_clock,
                    )
                ),
                check_availability=operator(world.check_availability()),
                list_bookings=operator(world.list_bookings()),
                create_manual_booking=operator(world.create_manual_booking()),
                cancel_booking=operator(world.cancel_booking()),
                reschedule_booking=operator(world.reschedule_booking()),
                update_booking_status=operator(world.update_booking_status()),
                list_leads=operator(world.list_leads()),
                update_lead_status=operator(world.update_lead_status()),
                list_handoffs=operator(world.list_handoffs()),
                resolve_handoff=operator(world.resolve_handoff()),
                list_unanswered_questions=operator(world.list_unanswered_questions()),
                answer_unanswered_question=operator(world.answer_unanswered_question()),
                get_dashboard_stats=operator(world.dashboard()),
                start_calendar_connection=operator(
                    StartGoogleCalendarConnectionUseCase(
                        business_repo=world.business_repo,
                        authorization_state_repo=state_repo,
                        calendar_client=google_client,
                        wall_clock=world.clock.wall_clock,
                    )
                ),
                complete_calendar_connection=operator(
                    CompleteGoogleCalendarConnectionUseCase(
                        authorization_state_repo=state_repo,
                        connection_repo=self.connection_repo,
                        calendar_client=google_client,
                        secret_cipher=cipher,
                        wall_clock=world.clock.wall_clock,
                    )
                ),
                disconnect_calendar=operator(
                    DisconnectGoogleCalendarUseCase(
                        connection_repo=self.connection_repo,
                        event_link_repo=link_repo,
                        calendar_client=google_client,
                        secret_cipher=cipher,
                    )
                ),
            )
        )
        self.application = application
        self.client = TestClient(application)

    def url(self, path: str) -> str:
        return f"/v1/businesses/{self.business.id}{path}"

    def get(
        self,
        path: str,
        token: str = STAFF_TOKEN,
        **params: str,
    ) -> Response:
        return self.client.get(
            self.url(path),
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

    def send(
        self,
        method: str,
        path: str,
        body: Mapping[str, object] | None = None,
        token: str = STAFF_TOKEN,
    ) -> Response:
        return self.client.request(
            method,
            self.url(path),
            json=body,
            headers={"Authorization": f"Bearer {token}"},
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

    assert len(paths) == 15
    assert "/v1/businesses/{business_id}/bookings/{booking_id}/reschedule" in paths
    assert GOOGLE_CALENDAR_CALLBACK_PATH in paths


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
    ):
        bad = api.get("/availability", **params)
        assert bad.status_code == 422, params
        assert bad.json()["error"] == "validation_failed"

    assert api.get("/availability").status_code == 422


def test_booking_lifecycle_through_the_cabinet() -> None:
    api = Api()

    created = api.send(
        "POST",
        "/bookings",
        {
            "contact_name": "Levan",
            "contact_phone_number": "599 12 34 56",
            "date": "2026-10-06",
            "time": "19:00",
            "party_size": 3,
            "source_channel": "phone",
            "notes": "Birthday",
        },
    )
    assert created.status_code == 201, created.text
    booking = created.json()["booking"]
    assert booking["contact_phone_number"] == "+995599123456"
    assert booking["status"] == "confirmed"
    assert "Levan" in created.json()["confirmation_text"]

    listed = api.get("/bookings", **{"from": "2026-10-06", "to": "2026-10-06"})
    assert [item["id"] for item in listed.json()["items"]] == [booking["id"]]
    assert api.get("/bookings", status="cancelled").json()["items"] == []

    moved = api.send(
        "POST",
        f"/bookings/{booking['id']}/reschedule",
        {"new_date": "2026-10-07", "new_time": "20:00"},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["booking"]["date"] == "2026-10-07"

    completed = api.send("PATCH", f"/bookings/{booking['id']}", {"status": "completed"})
    assert completed.json()["status"] == "completed"
    refused = api.send("POST", f"/bookings/{booking['id']}/cancel")
    assert refused.status_code == 409

    assert api.send("POST", "/bookings/booking_nope/cancel").status_code == 404
    invalid = api.send("PATCH", f"/bookings/{booking['id']}", {"status": "maybe"})
    assert invalid.status_code == 422
    assert "status" in invalid.json()["message"]
    extra = api.send(
        "POST", f"/bookings/{booking['id']}/reschedule", {"new_date": "x", "a": 1}
    )
    assert extra.status_code == 422


def test_cabinet_cancel_uses_the_requested_language() -> None:
    api = Api()
    created = api.send(
        "POST",
        "/bookings",
        {
            "contact_name": "Levan",
            "date": "2026-10-06",
            "time": "19:00",
            "party_size": 2,
        },
    ).json()["booking"]

    response = api.client.post(
        api.url(f"/bookings/{created['id']}/cancel"),
        params={"language": "en"},
        headers={"Authorization": f"Bearer {STAFF_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json()["confirmation_text"].startswith(
        "Your booking at Salobie Bia on Tuesday, October 6, 2026, 19:00 is cancelled."
    )


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

    assert api.get("/leads").json() == {"items": []}
    assert api.get("/leads", status="won").status_code == 200
    handoffs = api.get("/handoffs", status="notified").json()["items"]
    assert [item["id"] for item in handoffs] == [str(handoff.id)]
    resolved = api.send("POST", f"/handoffs/{handoff.id}/resolve")
    assert resolved.json()["status"] == "resolved"

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
    assert default.json()["date_to"] == "2026-10-05"
    assert (
        api.get("/dashboard", **{"from": "2026-10-05", "to": "2026-10-01"}).status_code
        == 422
    )


def test_google_calendar_connection_routes() -> None:
    api = Api()

    assert ROUTE_CALLBACK_PATH == GOOGLE_CALENDAR_CALLBACK_PATH
    staff = api.get("/integrations/google-calendar/connect-url")
    assert staff.status_code == 403
    connect = api.get("/integrations/google-calendar/connect-url", token=OWNER_TOKEN)
    assert connect.status_code == 200
    authorization_url = str(connect.json()["authorization_url"])
    state = parse_qs(urlsplit(authorization_url).query)["state"][0]

    denied = api.client.get(ROUTE_CALLBACK_PATH, params={"error": "access_denied"})
    assert denied.status_code == 422
    assert "access_denied" in denied.json()["message"]
    assert api.client.get(ROUTE_CALLBACK_PATH).status_code == 422
    callback = api.client.get(
        ROUTE_CALLBACK_PATH, params={"code": "good-code", "state": state}
    )
    assert callback.status_code == 200, callback.text
    assert callback.json()["calendar_id"] == "primary"
    assert api.connection_repo.get_by_business(api.business.id) is not None

    assert (
        api.send(
            "DELETE", "/integrations/google-calendar", token=STAFF_TOKEN
        ).status_code
        == 403
    )
    disconnected = api.send(
        "DELETE", "/integrations/google-calendar", token=OWNER_TOKEN
    )
    assert disconnected.json() == {
        "business_id": str(api.business.id),
        "was_connected": True,
    }
