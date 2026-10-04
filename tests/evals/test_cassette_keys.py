"""Keys of recorded model calls stay the same for the same conversation."""

import json

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.conversations.strings import LlmProviderPayload
from app.utilities.llm_cassettes.cassette_keys import (
    build_cassette_request,
    canonicalize_transcript,
    digest_tools,
    reserialize,
)
from tests.evals.eval_builders import llm_request, tool_definition, user_turn

FIRST_BOOKING: str = "booking_132e3658-4ca2-4ddd-a630-3fabc783b142"
SECOND_BOOKING: str = "booking_9b1c2a33-1111-4ddd-a630-3fabc783b142"


def tool_result_turn(booking_id: str, call_id: str) -> str:
    return json.dumps(
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": json.dumps({"booking_id": booking_id}),
                }
            ],
        }
    )


def test_random_ids_fence_keys_and_call_ids_become_numbered_placeholders() -> None:
    canonical = canonicalize_transcript(
        [
            LlmProviderPayload(payload)
            for payload in (
                user_turn("<customer_text 1a2b3c4d>\nHi\n</customer_text 1a2b3c4d>"),
                tool_result_turn(FIRST_BOOKING, "toolu_scripted_0001"),
                tool_result_turn(FIRST_BOOKING, "call_AbC123"),
            )
        ]
    )

    joined = "\n".join(canonical)
    assert "1a2b3c4d" not in joined
    assert "132e3658" not in joined
    assert "toolu_scripted_0001" not in joined
    assert "customer_text <fence:1>" in canonical[0]
    # The same booking keeps its placeholder; another call id gets a new one.
    assert canonical[1].count("booking_<id:") == canonical[2].count("booking_<id:")
    assert "<call:" in canonical[1] and "<call:" in canonical[2]


def test_the_key_ignores_ids_but_not_which_record_is_which() -> None:
    same_booking = llm_request(
        [
            tool_result_turn(FIRST_BOOKING, "toolu_1"),
            tool_result_turn(FIRST_BOOKING, "toolu_2"),
        ]
    )
    same_booking_again = llm_request(
        [
            tool_result_turn(SECOND_BOOKING, "toolu_7"),
            tool_result_turn(SECOND_BOOKING, "toolu_8"),
        ]
    )
    two_bookings = llm_request(
        [
            tool_result_turn(FIRST_BOOKING, "toolu_1"),
            tool_result_turn(SECOND_BOOKING, "toolu_2"),
        ]
    )

    first = build_cassette_request(same_booking)
    assert (
        first.request_digest
        == build_cassette_request(same_booking_again).request_digest
    )
    assert first.request_digest != build_cassette_request(two_bookings).request_digest


def test_every_part_of_the_request_changes_the_key() -> None:
    base = llm_request([user_turn("Hi")])
    variants = [
        llm_request([user_turn("Hello")]),
        llm_request([user_turn("Hi")], system_prompt="Another instruction."),
        llm_request([user_turn("Hi")], model="gpt-5-mini"),
        llm_request(
            [user_turn("Hi")],
            tools=[tool_definition(AssistantToolName.GET_PRICE, "Other words.")],
        ),
    ]

    keys = {
        build_cassette_request(request).request_digest for request in [base, *variants]
    }

    assert len(keys) == 5


def test_json_key_order_does_not_matter_and_other_text_is_kept() -> None:
    assert reserialize('{"b": 1, "a": 2}') == reserialize('{"a": 2, "b": 1}')
    assert reserialize("not json") == "not json"


def test_tools_digest_follows_the_offered_order() -> None:
    price = tool_definition(AssistantToolName.GET_PRICE)
    booking = tool_definition(AssistantToolName.CREATE_BOOKING)

    assert digest_tools([price, booking]) != digest_tools([booking, price])


def test_the_tail_keeps_the_end_of_the_last_turn() -> None:
    long_text = "x" * 2000 + "THE END"
    request = build_cassette_request(llm_request([user_turn(long_text)]))

    assert str(request.transcript_tail).endswith(
        'THE END", "type": "text"}], "role": "user"}'
    )
    assert len(str(request.transcript_tail)) == 600
    assert build_cassette_request(llm_request([])).transcript_tail == ""
