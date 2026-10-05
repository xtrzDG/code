"""The tool definitions offered to the model: strict schemas, order, hidden reasons."""

import json
from typing import Any, cast

import pytest

from app.registries.tools.assistant_tool_registry import AssistantToolRegistry
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.assistant_tools import (
    CancelBookingToolInput,
    CheckAvailabilityToolInput,
    CreateBookingToolInput,
    CreateLeadToolInput,
    GetPriceToolInput,
    HandoffToHumanToolInput,
    ListMyBookingsToolInput,
    RecordUnansweredQuestionToolInput,
    RescheduleBookingToolInput,
    SearchKnowledgeToolInput,
    SendLinkToolInput,
)

INPUT_MODELS: dict[AssistantToolName, type[Any]] = {
    AssistantToolName.SEARCH_KNOWLEDGE: SearchKnowledgeToolInput,
    AssistantToolName.GET_PRICE: GetPriceToolInput,
    AssistantToolName.CHECK_AVAILABILITY: CheckAvailabilityToolInput,
    AssistantToolName.CREATE_BOOKING: CreateBookingToolInput,
    AssistantToolName.CANCEL_BOOKING: CancelBookingToolInput,
    AssistantToolName.RESCHEDULE_BOOKING: RescheduleBookingToolInput,
    AssistantToolName.LIST_MY_BOOKINGS: ListMyBookingsToolInput,
    AssistantToolName.CREATE_LEAD: CreateLeadToolInput,
    AssistantToolName.HANDOFF_TO_HUMAN: HandoffToHumanToolInput,
    AssistantToolName.SEND_LINK: SendLinkToolInput,
    AssistantToolName.RECORD_UNANSWERED_QUESTION: RecordUnansweredQuestionToolInput,
}


SERVER_SIDE_FIELDS: set[str] = {
    "business_id",
    "contact_id",
    "conversation_id",
    "channel",
    "source_channel",
    "is_sandbox",
}


def walk_schemas(schema: dict[str, Any]) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = [schema]
    for value in schema.values():
        children: list[object] = (
            cast(list[object], value) if isinstance(value, list) else [value]
        )
        for child in children:
            if isinstance(child, dict):
                schemas.extend(walk_schemas(cast(dict[str, Any], child)))

    return schemas


@pytest.mark.parametrize("tool_name", list(AssistantToolName))
def test_every_tool_has_a_strict_schema_matching_its_input_dto(
    tool_name: AssistantToolName,
) -> None:
    definition = AssistantToolRegistry().get(tool_name)
    schema: dict[str, Any] = json.loads(definition.input_schema_json)

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["required"] == list(schema["properties"])
    assert set(schema["properties"]) == set(INPUT_MODELS[tool_name].model_fields)
    assert not set(schema["properties"]) & SERVER_SIDE_FIELDS
    for nested in walk_schemas(schema):
        assert not {"minimum", "maximum", "pattern", "format"} & set(nested)

    assert str(definition.description) != ""


def test_definitions_are_deterministic_and_deduplicated() -> None:
    first, second = AssistantToolRegistry(), AssistantToolRegistry()
    names = [AssistantToolName.GET_PRICE, AssistantToolName.SEND_LINK]

    assert first.list_definitions(names) == second.list_definitions(names)
    assert [
        definition.name
        for definition in first.list_definitions([*names, AssistantToolName.GET_PRICE])
    ] == names


def test_the_engine_only_reason_is_not_offered_to_the_model() -> None:
    schema = json.loads(
        AssistantToolRegistry()
        .get(AssistantToolName.HANDOFF_TO_HUMAN)
        .input_schema_json
    )

    assert "unverified_numbers" not in schema["properties"]["reason"]["enum"]
    assert "customer_request" in schema["properties"]["reason"]["enum"]
