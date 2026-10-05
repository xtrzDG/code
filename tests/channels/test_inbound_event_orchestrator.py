"""
The worker's side of the inbox (InboundEventOrchestrator): an event is
taken, processed and closed; a refusal fails it for good, a temporary
failure gives it back for the job's retry, and the last attempt fails it.
Whatever happens, the event is never left held by a job that gave up.
"""

import logging

import pytest

from app.orchestrators.channels.inbox.inbound_event_orchestrator import (
    InboundEventOrchestrator,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundAnswer, InboundEventClaim, InboundFailure
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from app.utilities.deliveries.inbound_failures import MAX_ERROR_TEXT_LENGTH


class Recorded[In, Out]:
    """A use case that records its inputs and answers as told (or raises)."""

    def __init__(self, answer: Out, failure: Exception | None = None) -> None:
        self.inputs: list[In] = []
        self._answer: Out = answer
        self._failure: Exception | None = failure

    def run(self, input_data: In) -> Out:
        self.inputs.append(input_data)
        if self._failure is not None:
            raise self._failure
        return self._answer


class ScriptedTurn(InboundEventOrchestrator):
    """An event kind whose processing answers or fails as the test says."""

    def __init__(self, world: World, failure: Exception | None) -> None:
        super().__init__(world.claim, world.finish, world.release)
        self.processed: list[InboundEventClaim] = []
        self._failure: Exception | None = failure

    def _process(self, claim: InboundEventClaim) -> InboundAnswer:
        self.processed.append(claim)
        if self._failure is not None:
            raise self._failure
        return InboundAnswer(event=claim.event, text=MessageText("Yes, at 19:00."))


class World:
    def __init__(
        self, claimed: bool = True, finish_failure: Exception | None = None
    ) -> None:
        self.business_id = BusinessId()
        provider_message_id = ProviderMessageId("update_1")
        self.event = InboundEventDocument(
            id=derive_inbound_event_id(
                self.business_id, ChannelKind.TELEGRAM, provider_message_id
            ),
            business_id=self.business_id,
            kind=InboundEventKind.CUSTOMER_MESSAGE,
            channel=ChannelKind.TELEGRAM,
            provider_message_id=provider_message_id,
        )
        claim = InboundEventClaim(event=self.event) if claimed else None
        self.claim = Recorded[QueuedJobInput, InboundEventClaim | None](claim)
        self.finish = Recorded[InboundAnswer, InboundEventDocument | None](
            self.event, finish_failure
        )
        self.release = Recorded[InboundFailure, InboundEventDocument | None](self.event)

    def job(self, is_final_attempt: bool = False) -> QueuedJobInput:
        return QueuedJobInput(
            job_id=QueuedJobId(),
            job_name=JobName("process_inbound_message"),
            payload=JobPayloadJson("{}"),
            business_id=self.business_id,
            is_final_attempt=is_final_attempt,
        )


def test_an_event_taken_by_another_worker_is_left_alone() -> None:
    world = World(claimed=False)
    turn = ScriptedTurn(world, failure=None)

    report = turn.execute(world.job())

    assert report == JobReport()
    assert (turn.processed, world.finish.inputs, world.release.inputs) == ([], [], [])


def test_a_processed_event_is_closed_with_its_answer() -> None:
    world = World()
    turn = ScriptedTurn(world, failure=None)

    report = turn.execute(world.job())

    assert int(report.processed_count) == 1
    [answer] = world.finish.inputs
    assert answer.event.id == world.event.id
    assert answer.text == MessageText("Yes, at 19:00.")
    assert world.release.inputs == []


def test_a_refusal_fails_the_event_for_good_and_ends_the_job(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = World()
    turn = ScriptedTurn(world, ValidationFailedError("The business is not live."))

    with caplog.at_level(logging.WARNING):
        report = turn.execute(world.job())

    assert report == JobReport()
    [failure] = world.release.inputs
    assert failure.is_final
    assert failure.event_id == world.event.id
    assert failure.business_id == world.business_id
    assert str(failure.error) == "The business is not live."
    assert world.finish.inputs == []
    assert "was not processed" in caplog.text


@pytest.mark.parametrize(
    "error",
    [ExternalServiceError("Telegram timed out"), RuntimeError("connection reset")],
    ids=["provider", "unexpected"],
)
def test_a_temporary_failure_gives_the_event_back_for_the_retry(
    error: Exception,
) -> None:
    world = World()
    turn = ScriptedTurn(world, error)

    with pytest.raises(type(error)):
        turn.execute(world.job(is_final_attempt=False))

    [failure] = world.release.inputs
    assert not failure.is_final
    assert world.finish.inputs == []


def test_a_temporary_failure_on_the_last_attempt_fails_the_event() -> None:
    world = World()
    turn = ScriptedTurn(world, ExternalServiceError("Meta is down"))

    with pytest.raises(ExternalServiceError):
        turn.execute(world.job(is_final_attempt=True))

    [failure] = world.release.inputs
    assert failure.is_final


def test_an_answer_that_cannot_be_closed_releases_the_event() -> None:
    world = World(finish_failure=ExternalServiceError("database away"))
    turn = ScriptedTurn(world, failure=None)

    with pytest.raises(ExternalServiceError):
        turn.execute(world.job())

    assert len(world.finish.inputs) == 1
    [failure] = world.release.inputs
    assert not failure.is_final
    assert str(failure.error) == "database away"


def test_a_long_error_is_kept_on_one_line_and_shortened() -> None:
    world = World()
    message = "line one\n\n   line two " + "x" * 2_000
    turn = ScriptedTurn(world, ExternalServiceError(message))

    with pytest.raises(ExternalServiceError):
        turn.execute(world.job())

    [failure] = world.release.inputs
    text = str(failure.error)
    assert "\n" not in text
    assert text.startswith("line one line two x")
    assert len(text) == MAX_ERROR_TEXT_LENGTH
    assert text.endswith("…")
