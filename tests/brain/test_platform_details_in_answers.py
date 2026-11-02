"""
What only platform admins read in the API's answers (OWASP API3, ASVS
V15.3.1): the inputs and results of the assistant's tool calls, the model,
tokens and cost of a message and the conversation's usage. Owners and
staff get the same answers without them (the tool's name and whether it
failed stay); being on the admin team is read at every request.
"""

from typing import Any

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.users import UserDocument
from app.schemas.typings.users.booleans import IsPlatformAdmin
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.cabinet_http import bearer
from tests.brain.conversation_feed_helpers import cabinet
from tests.brain.platform_details_fakes import see_platform_details
from tests.brain.scripted_turns import call_tool, say, scripted

TOOL_INPUT: str = '{"item_name":"khinkali"}'
PLATFORM_FIELDS: tuple[str, ...] = (
    "model_id",
    "input_tokens",
    "output_tokens",
    "cost_micro_usd",
)


def priced_world() -> BrainWorld:
    """Two turns that each look the price up before answering."""

    return build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, TOOL_INPUT),
            say("Хинкали — 1,20 лари."),
            call_tool(AssistantToolName.GET_PRICE, TOOL_INPUT),
            say("Хинкали — 1,20 лари."),
        )
    )


def card(world: BrainWorld, admins: frozenset[UserId], token: str) -> dict[str, Any]:
    reply = world.send("Сколько стоят хинкали?")
    response = cabinet(world, platform_admins=admins).get(
        f"/v1/businesses/{world.business.id}/conversations/{reply.conversation_id}",
        headers=bearer(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_the_owner_reads_the_card_without_platform_details() -> None:
    world = priced_world()

    body = card(world, frozenset(), "owner")

    answer: dict[str, Any] = body["messages"][1]
    assert [call["tool_name"] for call in answer["tool_calls"]] == ["get_price"]
    assert answer["tool_calls"][0]["is_error"] is False
    assert answer["tool_calls"][0]["input_json"] is None
    assert answer["tool_calls"][0]["result_json"] is None
    assert [answer[name] for name in PLATFORM_FIELDS] == [None] * 4
    assert body["usage"] is None
    assert answer["text"].endswith("Хинкали — 1,20 лари.")


def test_a_platform_admin_reads_every_detail() -> None:
    world = priced_world()

    body = card(world, frozenset({world.owner_id}), "owner")

    answer: dict[str, Any] = body["messages"][1]
    assert answer["tool_calls"][0]["input_json"] == TOOL_INPUT
    assert '"price":"1.20"' in answer["tool_calls"][0]["result_json"]
    assert answer["model_id"] == "scripted"
    assert all(answer[name] is not None for name in PLATFORM_FIELDS)
    assert body["usage"] is not None


def test_earlier_pages_of_the_transcript_are_filtered_the_same_way() -> None:
    world = priced_world()
    reply = world.send("Сколько стоят хинкали?")
    url = (
        f"/v1/businesses/{world.business.id}/conversations/"
        f"{reply.conversation_id}/messages"
    )

    team = cabinet(world).get(url, headers=bearer("staff")).json()
    admin = (
        cabinet(world, platform_admins=frozenset({world.staff_id}))
        .get(url, headers=bearer("staff"))
        .json()
    )

    team_answer = next(item for item in team["items"] if item["tool_calls"])
    admin_answer = next(item for item in admin["items"] if item["tool_calls"])
    assert team_answer["tool_calls"][0]["input_json"] is None
    assert team_answer["model_id"] is None
    assert admin_answer["tool_calls"][0]["input_json"] == TOOL_INPUT
    assert admin_answer["model_id"] == "scripted"


def test_the_test_chat_shows_tool_inputs_to_platform_admins_only() -> None:
    world = priced_world()
    url = f"/v1/businesses/{world.business.id}/test-chat"
    question = {"text": "Сколько стоят хинкали?"}

    owner = cabinet(world).post(url, json=question, headers=bearer("owner")).json()
    admin = (
        cabinet(world, platform_admins=frozenset({world.owner_id}))
        .post(url, json=question, headers=bearer("owner"))
        .json()
    )

    assert owner["tool_calls"][0]["tool_name"] == "get_price"
    assert owner["tool_calls"][0]["input_json"] is None
    assert owner["tool_calls"][0]["result_json"] is None
    assert admin["tool_calls"][0]["input_json"] == TOOL_INPUT
    assert '"price":"1.20"' in admin["tool_calls"][0]["result_json"]


def test_the_admin_team_decides_never_the_stored_flag() -> None:
    world = priced_world()
    owner: UserDocument | None = world.user_repo.get(world.owner_id)
    assert owner is not None
    world.user_repo.save(owner.model_copy(update={"is_platform_admin": True}))
    sees: UseCaseContract[UserId, IsPlatformAdmin] = see_platform_details(
        world, frozenset({world.staff_id})
    )

    assert sees.run(world.owner_id) is False
    assert sees.run(world.staff_id) is True
    assert sees.run(UserId()) is False

