"""Small fakes of the channels tests: clock, cipher, voice tools, greeting, auth."""

import json

from typed_time_provider import Microseconds, WallClock

from app.contracts.conversation_flow import VoiceToolCallOrchestratorContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.repositories.business_repositories import BusinessRepository
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import (
    CallGreeting,
    CallGreetingRequest,
    VoiceToolCallRequest,
    VoiceToolCallResult,
)
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.conversations.strings import LlmToolResultJson, MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from tests.foundation.access_support import signed_in

NANOSECONDS_PER_SECOND: int = 1_000_000_000


# 2026-10-01 12:00:00 UTC.
START_UNIX_SECONDS: int = 1_790_856_000


class RecordingVoiceAgentRemoval:
    """Records the businesses whose voice agent was switched off."""

    def __init__(self, business_ids: list[BusinessId]) -> None:
        self.business_ids: list[BusinessId] = business_ids

    def run(self, input_data: BusinessId) -> None:
        self.business_ids.append(input_data)


class AdjustableClock:
    """Unix time that tests move forward explicitly."""

    def __init__(self, start_seconds: int = START_UNIX_SECONDS) -> None:
        self.nanoseconds: int = start_seconds * NANOSECONDS_PER_SECOND

    def read(self) -> int:
        return self.nanoseconds

    def advance(self, seconds: int) -> None:
        self.nanoseconds += seconds * NANOSECONDS_PER_SECOND

    def advance_microseconds(self, microseconds: int) -> None:
        self.nanoseconds += microseconds * 1000

    def build_wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=self.read,
        )

    def now_seconds(self) -> int:
        return self.nanoseconds // NANOSECONDS_PER_SECOND

    def now_microseconds(self) -> Microseconds:
        return Microseconds(self.nanoseconds // 1000)


class FakeSecretCipher(SecretCipherAdapterContract):
    """Reversible stand-in for the Fernet cipher; ciphertext never equals plaintext."""

    PREFIX: str = "sealed:"

    def encrypt(self, secret: ChannelSecret) -> EncryptedChannelSecret:
        return EncryptedChannelSecret(self.PREFIX + str(secret)[::-1])

    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        text: str = str(encrypted_secret)
        if not text.startswith(self.PREFIX):
            raise ValidationFailedError("Invalid ciphertext.")

        return ChannelSecret(text.removeprefix(self.PREFIX)[::-1])


class FakeVoiceToolCallOrchestrator(VoiceToolCallOrchestratorContract):
    def __init__(self) -> None:
        self.requests: list[VoiceToolCallRequest] = []

    def execute(self, input_data: VoiceToolCallRequest) -> VoiceToolCallResult:
        self.requests.append(input_data)
        return VoiceToolCallResult(
            result_json=LlmToolResultJson(
                json.dumps({"ok": True, "tool": input_data.tool_name.value})
            )
        )


class FakeCallGreetingUseCase(UseCaseContract[CallGreetingRequest, CallGreeting]):
    def __init__(self, business_repo: BusinessRepository) -> None:
        self._business_repo: BusinessRepository = business_repo
        self.requests: list[CallGreetingRequest] = []

    def run(self, input_data: CallGreetingRequest) -> CallGreeting:
        self.requests.append(input_data)
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        assert business is not None
        language: LanguageTag = input_data.language or business.default_language
        return CallGreeting(
            text=MessageText(f"[{language}] AI assistant of {business.name}."),
            language=language,
        )


class FakeAuthenticationOperator(OperatorContract[AccessToken, SessionAssurance]):
    def __init__(self) -> None:
        self.users_by_token: dict[str, UserId] = {}

    def operate(self, input_data: AccessToken) -> SessionAssurance:
        user_id: UserId | None = self.users_by_token.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return signed_in(user_id)


class RecordingHandoffToHuman(UseCaseContract[HandoffCommand, HandoffResult]):
    """Records the handoffs the outbox asks for (undelivered replies)."""

    def __init__(self) -> None:
        self.commands: list[HandoffCommand] = []

    def run(self, input_data: HandoffCommand) -> HandoffResult:
        self.commands.append(input_data)
        return HandoffResult(
            id=HandoffId(),
            business_id=input_data.business_id,
            conversation_id=input_data.conversation_id,
            reason=input_data.reason,
            urgency=input_data.urgency,
            status=HandoffStatus.PENDING,
            customer_message=MessageText("A colleague will reply soon."),
        )


class RecordingOrchestrator[InputData, OutputData](
    OrchestratorContract[InputData, OutputData]
):
    """Runs an orchestrator and keeps what it returned."""

    def __init__(
        self,
        orchestrator: OrchestratorContract[InputData, OutputData],
        outputs: list[OutputData],
    ) -> None:
        self._orchestrator: OrchestratorContract[InputData, OutputData] = orchestrator
        self._outputs: list[OutputData] = outputs

    def execute(self, input_data: InputData) -> OutputData:
        output: OutputData = self._orchestrator.execute(input_data)
        self._outputs.append(output)
        return output
