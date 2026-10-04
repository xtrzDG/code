"""
The operations routes on a small FastAPI app with token login, as the cabinet calls
them.
"""

from collections.abc import Mapping

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.operator_contract import OperatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.gateways.http.error_responses import install_error_handlers
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
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
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
from app.use_cases.calendar.get_google_calendar_connection_use_case import (
    GetGoogleCalendarConnectionUseCase,
)
from app.use_cases.calendar.start_google_calendar_connection_use_case import (
    StartGoogleCalendarConnectionUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.foundation.access_support import ACCESS_SETTINGS, signed_in
from tests.operations.fake_google import FakeGoogle
from tests.operations.fakes import ReversingSecretCipher
from tests.operations.operations_world import OperationsWorld

OWNER_TOKEN: str = "owner-token"


STAFF_TOKEN: str = "staff-token"


STRANGER_TOKEN: str = "stranger-token"


CABINET_URL: str = "https://cabinet.example.com"


def operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> OperatorContract[InputData, OutputData]:
    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))


class TokenAuthenticator(OperatorContract[AccessToken, SessionAssurance]):
    def __init__(self, users: dict[str, UserId]) -> None:
        self._users: dict[str, UserId] = users

    def operate(self, input_data: AccessToken) -> SessionAssurance:
        user_id: UserId | None = self._users.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return signed_in(user_id)


class Api:
    """The operations router over an in-memory Tbilisi restaurant."""

    def __init__(self, cabinet_base_url: str | None = CABINET_URL) -> None:
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
                    ),
                    SessionAssuranceContext(),
                ),
                authorize_business_access=operator(
                    AuthorizeBusinessAccessUseCase(
                        business_repo=world.business_repo,
                        user_repo=world.user_repo,
                        audit_log_repo=world.audit_repo,
                        wall_clock=world.clock.wall_clock,
                        session_assurance=SessionAssuranceContext(),
                        app_settings=ACCESS_SETTINGS,
                    )
                ),
                check_availability=operator(world.check_availability()),
                list_bookings=operator(world.list_bookings()),
                create_manual_booking=operator(world.create_manual_booking()),
                cancel_booking=operator(world.cancel_booking()),
                reschedule_booking=operator(world.reschedule_booking()),
                update_booking=operator(world.update_booking()),
                revert_booking_status=operator(world.revert_booking_status()),
                list_leads=operator(world.list_leads()),
                update_lead_status=operator(world.update_lead_status()),
                list_handoffs=operator(world.list_handoffs()),
                resolve_handoff=operator(world.resolve_handoff()),
                reopen_handoff=operator(world.reopen_handoff()),
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
                get_calendar_connection=operator(
                    GetGoogleCalendarConnectionUseCase(
                        connection_repo=self.connection_repo,
                        calendar_client=google_client,
                    )
                ),
                cabinet_base_url=(
                    None
                    if cabinet_base_url is None
                    else CabinetBaseUrl(cabinet_base_url)
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
