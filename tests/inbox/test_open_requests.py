"""Requests keep their conversation in the "Requests" view while they are open."""

import logging

import pytest

from app.schemas.constants.bookings import LeadStatus
from app.schemas.domain.bookings import LeadDocument
from app.schemas.dto.inbox.assignment import (
    AutoAssignCommand,
    AutoAssignResult,
    OpenRequestRefresh,
    OpenRequestState,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.use_cases.shared.request_tracking import track_request
from tests.inbox.inbox_builders import reload, request, talk
from tests.inbox.inbox_world import InboxWorld


def refresh(world: InboxWorld, lead: LeadDocument) -> OpenRequestState:
    assert lead.conversation_id is not None
    return world.refresh_open_request().run(
        OpenRequestRefresh(
            business_id=world.business.id, conversation_id=lead.conversation_id
        )
    )


def close(world: InboxWorld, lead: LeadDocument, status: LeadStatus) -> None:
    lead.status = status
    world.lead_repo.save(lead)
    refresh(world, lead)


def test_a_conversation_waits_while_one_of_its_requests_is_open() -> None:
    world = InboxWorld()
    conversation = talk(world, "Dato", minutes_ago=3)
    first = request(world, conversation)
    second = request(world, conversation, LeadStatus.IN_PROGRESS)
    assert reload(world, conversation).has_open_request is True

    close(world, first, LeadStatus.WON)
    assert reload(world, conversation).awaits_team is True

    close(world, second, LeadStatus.LOST)
    stored = reload(world, conversation)
    assert (stored.has_open_request, stored.awaits_team) == (False, False)


def test_reopening_a_request_brings_the_conversation_back() -> None:
    world = InboxWorld()
    conversation = talk(world, "Dato", minutes_ago=3)
    lead = request(world, conversation, LeadStatus.WON)
    assert reload(world, conversation).has_open_request is False

    close(world, lead, LeadStatus.NEW)

    assert refresh(world, lead).has_open_request is True
    assert reload(world, conversation).has_open_request is True


class FailingRefresh:
    def run(self, input_data: OpenRequestRefresh) -> OpenRequestState:
        raise ExternalServiceError(f"Storage is down for {input_data.conversation_id}.")


class RecordingAutoAssign:
    def __init__(self) -> None:
        self.commands: list[AutoAssignCommand] = []

    def run(self, input_data: AutoAssignCommand) -> AutoAssignResult:
        self.commands.append(input_data)
        return AutoAssignResult()


def test_tracking_a_new_request_refreshes_and_assigns() -> None:
    world = InboxWorld()
    conversation = talk(world, "Dato", minutes_ago=3)
    lead = request(world, conversation)
    assigner = RecordingAutoAssign()

    track_request(lead, world.refresh_open_request(), assigner)

    assert [command.conversation_id for command in assigner.commands] == [
        conversation.id
    ]


def test_a_request_without_a_conversation_is_left_alone() -> None:
    world = InboxWorld()
    conversation = talk(world, "Dato", minutes_ago=3)
    lead = request(world, conversation).model_copy(update={"conversation_id": None})
    assigner = RecordingAutoAssign()

    track_request(lead, FailingRefresh(), assigner)

    assert assigner.commands == []


def test_a_failed_refresh_never_fails_the_request(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = InboxWorld()
    lead = request(world, talk(world, "Dato", minutes_ago=3))

    with caplog.at_level(logging.ERROR):
        track_request(lead, FailingRefresh())

    assert "could not take request" in caplog.text
