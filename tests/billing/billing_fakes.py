"""Small fakes of the billing tests: clock, notifier, voice agent removal and auth."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.use_case_contract import UseCaseContract
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.repositories.user_repositories import UserRepository
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from tests.billing.billing_settings import (
    MICROSECONDS_PER_DAY,
    MICROSECONDS_PER_HOUR,
    NANOSECONDS_PER_MICROSECOND,
    START_NANOSECONDS,
)
from tests.foundation.access_support import signed_in


class RecordingVoiceAgentRemoval:
    """Records the businesses whose voice agent was switched off."""

    def __init__(self) -> None:
        self.business_ids: list[BusinessId] = []

    def run(self, input_data: BusinessId) -> None:
        self.business_ids.append(input_data)


class AdjustableClock:
    """Wall clock whose time tests move forward explicitly."""

    def __init__(self, unix_nanoseconds: int = START_NANOSECONDS) -> None:
        self.unix_nanoseconds: int = unix_nanoseconds
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.unix_nanoseconds,
        )

    def now(self) -> Microseconds:
        return Microseconds(self.unix_nanoseconds // NANOSECONDS_PER_MICROSECOND)

    def advance(self, days: float = 0, hours: float = 0) -> None:
        self.unix_nanoseconds += int(
            (days * MICROSECONDS_PER_DAY + hours * MICROSECONDS_PER_HOUR)
            * NANOSECONDS_PER_MICROSECOND
        )

    def move_to(self, instant: Microseconds) -> None:
        self.unix_nanoseconds = int(instant) * NANOSECONDS_PER_MICROSECOND


class RecordingNotifier(ManagerNotificationFacilitatorContract):
    """Keeps every notification; delivery can be switched off."""

    def __init__(self) -> None:
        self.sent: list[tuple[ManagerContact, MessageText]] = []
        self.is_delivering: bool = True

    def notify(self, notification: StaffNotification) -> bool:
        self.sent.append((notification.contact, notification.text))
        return self.is_delivering

    def texts(self) -> list[str]:
        return [str(text) for _, text in self.sent]


class TokenAuthenticationOperator(OperatorContract[AccessToken, SessionAssurance]):
    """Bearer token = user id of a known user (tests only)."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo: UserRepository = user_repo

    def operate(self, input_data: AccessToken) -> SessionAssurance:
        try:
            user_id = UserId(str(input_data))
        except ValueError as error:
            raise AuthenticationRequiredError("Unknown token.") from error

        if self._user_repo.get(user_id) is None:
            raise AuthenticationRequiredError("Unknown token.")

        return signed_in(user_id)


def build_operator[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> PipelineOperator[InputData, OutputData]:
    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))
