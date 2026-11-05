"""
A voice check adapter that plays every simulated call by script: what the
agent says, which tools it calls and how the platform judges the call.
"""

import json
from collections.abc import Callable

from app.contracts.voice_platform import VoiceCheckAdapterContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.voice_checks import VoiceCheckStatus
from app.schemas.dto.voice_checks import (
    VoiceCheckBatch,
    VoiceCheckCase,
    VoiceCheckLine,
    VoiceCheckOutcome,
    VoiceCheckToolCall,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.strings import LlmToolInputJson, MessageText
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.voice.strings import VoiceCheckRationale

type CallScript = Callable[[VoiceCheckBatch, VoiceCheckCase], VoiceCheckOutcome]
# What the agent says once it booked, in each language of the checks.
CONFIRMATIONS: dict[str, str] = {
    "ka": "ჯავშანი მზადაა: ხვალ, 19:00, ორი ადამიანი.",
    "ru": "Бронь готова: завтра в 19:00, двое гостей.",
    "en": "Your table is booked for two tomorrow at 7 pm.",
}


def booking_call(party_size: int = 2) -> CallScript:
    """The agent greets in the case's language and books for `party_size`."""

    def play(batch: VoiceCheckBatch, case: VoiceCheckCase) -> VoiceCheckOutcome:
        greeting: str = next(
            str(greeting.text)
            for greeting in batch.agent.greetings
            if greeting.language == case.language
        )
        return VoiceCheckOutcome(
            key=case.key,
            status=VoiceCheckStatus.PASSED,
            lines=[
                VoiceCheckLine(
                    author=MessageAuthor.ASSISTANT, text=MessageText(greeting)
                ),
                VoiceCheckLine(
                    author=MessageAuthor.CUSTOMER, text=MessageText("A table, please.")
                ),
                VoiceCheckLine(
                    author=MessageAuthor.ASSISTANT,
                    text=MessageText(CONFIRMATIONS.get(str(case.language), "Booked.")),
                ),
            ],
            tool_calls=[
                VoiceCheckToolCall(
                    tool_name=AssistantToolName.CREATE_BOOKING,
                    input_json=LlmToolInputJson(
                        json.dumps({"arguments": {"party_size": party_size}})
                    ),
                )
            ],
            rationale=[VoiceCheckRationale("The booking was read back.")],
            cost_micro_usd=CostMicroUsd(12_000),
        )

    return play


class FakeVoiceCheckAdapter(VoiceCheckAdapterContract):
    """
    Plays each case with `script` and records every batch. Not configured
    until a test empties `missing_settings`, so other tests plan no voice
    checks; `error` fails the whole batch (the agent could not be set up).
    """

    def __init__(self) -> None:
        self.missing_settings: list[EnvironmentVariableName] = [
            EnvironmentVariableName("ELEVENLABS_API_KEY")
        ]
        self.script: CallScript = booking_call()
        self.error: ExternalServiceError | None = None
        self.batches: list[VoiceCheckBatch] = []

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        return list(self.missing_settings)

    def run_checks(self, batch: VoiceCheckBatch) -> list[VoiceCheckOutcome]:
        self.batches.append(batch)
        if self.error is not None:
            raise self.error

        return [self.script(batch, case) for case in batch.cases]
