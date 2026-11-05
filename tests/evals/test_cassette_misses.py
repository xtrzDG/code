"""A replayed call without a recording says which part of the request changed."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.llm_cassettes import LlmCassetteEntry, LlmCassetteRequest
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.evaluations.constrained_strings import (
    LlmInstructionDigest,
    LlmToolsDigest,
)
from app.utilities.llm_cassettes.cassette_keys import build_cassette_request
from app.utilities.llm_cassettes.cassette_misses import (
    MAX_DIFF_LINES,
    explain_cassette_miss,
    explain_instruction_change,
    explain_tools_change,
)
from tests.evals.eval_builders import llm_request, tool_definition, user_turn

PRICE = AssistantToolName.GET_PRICE
BOOKING = AssistantToolName.CREATE_BOOKING


def entry(request: LlmCassetteRequest) -> LlmCassetteEntry:
    return LlmCassetteEntry(request=request, takes=[])


def explain(
    now: LlmCassetteRequest,
    recorded: list[LlmCassetteRequest],
    instructions: dict[LlmInstructionDigest, str] | None = None,
    tools: dict[LlmToolsDigest, list[AssistantToolName]] | None = None,
) -> str:
    known_instructions = instructions or {}
    known_tools = tools or {}
    return str(
        explain_cassette_miss(
            now,
            SystemPromptText("Rule one.\nRule two, changed."),
            [PRICE, BOOKING],
            [entry(request) for request in recorded],
            lambda digest: (
                None
                if digest not in known_instructions
                else SystemPromptText(known_instructions[digest])
            ),
            lambda digest: known_tools.get(digest),
        )
    )


def test_a_changed_instruction_shows_a_diff() -> None:
    recorded = build_cassette_request(
        llm_request([user_turn("Hi")], system_prompt="Rule one.\nRule two.")
    )
    now = build_cassette_request(
        llm_request([user_turn("Hi")], system_prompt="Rule one.\nRule two, changed.")
    )

    reason = explain(
        now, [recorded], {recorded.instruction_digest: "Rule one.\nRule two."}
    )

    assert reason.startswith("The instruction changed since the recording:")
    assert "-Rule two." in reason
    assert "+Rule two, changed." in reason


def test_an_instruction_without_its_old_text_is_still_named() -> None:
    recorded = build_cassette_request(
        llm_request([user_turn("Hi")], system_prompt="Old.")
    )
    now = build_cassette_request(llm_request([user_turn("Hi")], system_prompt="New."))

    assert "its old text was not kept" in explain(now, [recorded])


def test_a_long_diff_is_cut() -> None:
    old = SystemPromptText("\n".join(f"line {number}" for number in range(200)))
    new = SystemPromptText("\n".join(f"row {number}" for number in range(200)))

    reason = str(explain_instruction_change(old, new))

    assert "more diff lines" in reason
    assert len(reason.splitlines()) <= MAX_DIFF_LINES + 2


def test_changed_tools_are_named() -> None:
    recorded = build_cassette_request(
        llm_request([user_turn("Hi")], tools=[tool_definition(PRICE)])
    )
    now = build_cassette_request(
        llm_request(
            [user_turn("Hi")],
            tools=[tool_definition(PRICE), tool_definition(BOOKING)],
        )
    )

    reason = explain(
        now,
        [recorded],
        tools={recorded.tools_digest: [PRICE, AssistantToolName.SEND_LINK]},
    )

    assert "added create_booking" in reason
    assert "removed send_link" in reason


def test_tool_changes_without_names_or_with_the_same_names() -> None:
    assert "tool definitions changed" in str(explain_tools_change(None, [PRICE]))
    assert "descriptions or input schemas" in str(
        explain_tools_change([PRICE], [PRICE])
    )


def test_another_model_is_named() -> None:
    recorded = build_cassette_request(
        llm_request([user_turn("Hi")], model="gpt-5-mini")
    )
    now = build_cassette_request(llm_request([user_turn("Hi")], model="scripted"))

    assert explain(now, [recorded]) == (
        "The cassette was recorded with model gpt-5-mini; this run asks scripted."
    )


def test_another_path_shows_the_closest_recorded_turn() -> None:
    far = build_cassette_request(llm_request([user_turn("Completely different words")]))
    close = build_cassette_request(llm_request([user_turn("How much is the room?")]))
    now = build_cassette_request(llm_request([user_turn("How much is the suite?")]))

    reason = explain(now, [far, close])

    assert reason.startswith("The conversation took another path")
    assert "Closest recorded:" in reason
    assert "the room?" in reason.split("Closest recorded:")[1]


def test_nothing_recorded_for_the_instruction() -> None:
    now = build_cassette_request(llm_request([user_turn("Hi")], system_prompt="Fresh."))

    assert "No call with this instruction" in explain(now, [])
