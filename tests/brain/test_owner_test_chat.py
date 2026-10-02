"""The owner's test chat: sandbox answers, sessions, versions, tool calls and errors."""

from typing import Any

import pytest

from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import SystemPromptText
from tests.brain.brain_world import build_world
from tests.brain.cabinet_http import bearer
from tests.brain.conversation_feed_helpers import cabinet
from tests.brain.scripted_turns import call_tool, say, scripted


def test_owner_test_chat_answers_from_the_published_version_in_a_sandbox() -> None:
    world = build_world(scripted(say("გამარჯობა!"), say("კი, გვაქვს.")))
    client = cabinet(world)
    url = f"/v1/businesses/{world.business.id}/test-chat"

    first = client.post(url, json={"text": "გამარჯობა"}, headers=bearer("owner"))
    second = client.post(url, json={"text": "ხინკალი გაქვთ?"}, headers=bearer("owner"))

    assert first.status_code == 200
    assert first.json()["text"].startswith("გამარჯობა! მე ვარ Sakhli-ის AI-ასისტენტი.")
    assert second.json()["text"] == "კი, გვაქვს."
    assert first.json()["conversation_id"] == second.json()["conversation_id"]
    conversation = world.conversations()[0]
    assert conversation.channel is ChannelKind.OWNER_TEST
    assert conversation.is_sandbox is True
    assert conversation.channel_user_id == f"owner:{world.owner_id}:default"
    assert world.usage_events() == []


def test_test_chat_sessions_and_versions() -> None:
    world = build_world(
        scripted(say("draft two"), say("ready one"), say("other tab")),
        is_published=False,
    )
    draft = world.version.model_copy(
        update={
            "id": AssistantVersionId(),
            "version_number": AssistantVersionNumber(2),
            "status": AssistantVersionStatus.DRAFT,
            "prompt_text": SystemPromptText("Draft two."),
        }
    )
    world.version_repo.save(draft)
    client = cabinet(world)
    url = f"/v1/businesses/{world.business.id}/test-chat"

    newest = client.post(url, json={"text": "Hi"}, headers=bearer("staff"))
    chosen_ready = client.post(
        url,
        json={"text": "Hi", "assistant_version_id": str(world.version.id)},
        headers=bearer("staff"),
    )
    other_tab = client.post(
        url,
        json={"text": "Hi", "session_key": "tab-2"},
        headers=bearer("staff"),
    )

    assert newest.status_code == 200
    assert (
        len(
            {
                newest.json()["conversation_id"],
                chosen_ready.json()["conversation_id"],
                other_tab.json()["conversation_id"],
            }
        )
        == 3
    )
    conversations = {
        str(conversation.id): conversation for conversation in world.conversations()
    }
    # Without a choice the newest version answers, here the draft.
    assert conversations[newest.json()["conversation_id"]].assistant_version_id == (
        draft.id
    )
    assert (newest.json()["assistant_version_id"], newest.json()["text"]) == (
        str(draft.id),
        newest.json()["disclosure_text"] + "\ndraft two",
    )
    assert newest.json()["assistant_version_number"] == 2
    assert conversations[
        chosen_ready.json()["conversation_id"]
    ].assistant_version_id == (world.version.id)
    assert chosen_ready.json()["assistant_version_number"] == 1


@pytest.mark.parametrize(
    "status",
    [AssistantVersionStatus.TESTS_FAILED, AssistantVersionStatus.TESTING],
)
def test_test_chat_prefers_a_newer_version_under_work_to_the_live_one(
    status: AssistantVersionStatus,
) -> None:
    world = build_world(scripted(say("newer")))
    archived = world.version.model_copy(
        update={
            "id": AssistantVersionId(),
            "version_number": AssistantVersionNumber(3),
            "status": AssistantVersionStatus.ARCHIVED,
        }
    )
    newer = world.version.model_copy(
        update={
            "id": AssistantVersionId(),
            "version_number": AssistantVersionNumber(2),
            "status": status,
        }
    )
    world.version_repo.save(archived)
    world.version_repo.save(newer)
    client = cabinet(world)

    reply = client.post(
        f"/v1/businesses/{world.business.id}/test-chat",
        json={"text": "Hi"},
        headers=bearer("owner"),
    )

    assert reply.status_code == 200, reply.text
    assert reply.json()["assistant_version_id"] == str(newer.id)
    assert reply.json()["assistant_version_number"] == 2


def test_test_chat_reply_carries_the_tool_calls_of_the_turn() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khinkali"}'),
            say("Хинкали — 1,20 лари."),
            say("Пожалуйста."),
        )
    )
    client = cabinet(world)
    url = f"/v1/businesses/{world.business.id}/test-chat"

    first = client.post(
        url, json={"text": "Сколько стоят хинкали?"}, headers=bearer("owner")
    )
    second = client.post(url, json={"text": "Спасибо"}, headers=bearer("owner"))

    assert first.status_code == 200, first.text
    body: dict[str, Any] = first.json()
    assert body["assistant_version_id"] == str(world.version.id)
    assert body["assistant_version_number"] == 1
    assert [call["tool_name"] for call in body["tool_calls"]] == ["get_price"]
    assert body["tool_calls"][0]["input_json"] == '{"item_name":"khinkali"}'
    assert '"price":"1.20"' in body["tool_calls"][0]["result_json"]
    assert body["tool_calls"][0]["is_error"] is False
    assert second.json()["tool_calls"] == []
    # The reply is enough: no conversation card was opened, nothing audited.
    assert world.audit_log_repo.list_by_business(world.business.id) == []


def test_test_chat_errors() -> None:
    world = build_world(scripted(say("x")), is_published=False)
    world.version.status = AssistantVersionStatus.ARCHIVED
    world.version_repo.save(world.version)
    client = cabinet(world)
    url = f"/v1/businesses/{world.business.id}/test-chat"

    responses = {
        "no version": client.post(url, json={"text": "Hi"}, headers=bearer("owner")),
        "unknown version": client.post(
            url,
            json={"text": "Hi", "assistant_version_id": str(AssistantVersionId())},
            headers=bearer("owner"),
        ),
        "empty text": client.post(url, json={"text": "  "}, headers=bearer("owner")),
        "bad session": client.post(
            url, json={"text": "Hi", "session_key": "tab 2!"}, headers=bearer("owner")
        ),
        "extra field": client.post(
            url,
            json={"text": "Hi", "business_id": str(world.business.id)},
            headers=bearer("owner"),
        ),
        "stranger": client.post(url, json={"text": "Hi"}, headers=bearer("stranger")),
    }

    assert {name: response.status_code for name, response in responses.items()} == {
        "no version": 409,
        "unknown version": 404,
        "empty text": 422,
        "bad session": 422,
        "extra field": 422,
        "stranger": 404,
    }
