from typing import Any

from fastapi.testclient import TestClient
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName, AssistantVersionStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import CallOutcome
from app.schemas.domain.conversations import CallDocument
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.constrained_integers import CallDurationSeconds
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.conversations.strings import (
    CallTranscriptText,
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import BrainWorld, build_world, call_tool, say, scripted
from tests.brain.cabinet_http import bearer, build_cabinet_client


class UnusedMenuExtractor:
    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        raise AssertionError("Menu extraction is not part of these tests.")


def cabinet(world: BrainWorld) -> TestClient:
    return build_cabinet_client(
        world,
        UnusedMenuExtractor(),
        {"owner": world.owner_id, "staff": world.staff_id, "stranger": UserId()},
    )


def seed_conversations(world: BrainWorld) -> None:
    world.send("Здравствуйте, есть столик?", name="Нино")
    world.send(
        "Hi from Telegram",
        channel=ChannelKind.TELEGRAM,
        user_id="tg-1",
        phone=None,
    )
    world.send("Sandbox check", is_sandbox=True, user_id="autotest", phone=None)


def test_feed_lists_conversations_with_filters() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khinkali"}'),
            say("Да, есть."),
            say("Hello!"),
            say("Sandbox reply"),
        )
    )
    seed_conversations(world)
    client = cabinet(world)
    base_url = f"/v1/businesses/{world.business.id}/conversations"

    everything = client.get(base_url, headers=bearer("owner"))
    with_sandbox = client.get(
        f"{base_url}?include_sandbox=true", headers=bearer("staff")
    )
    telegram = client.get(f"{base_url}?channel=telegram", headers=bearer("owner"))

    assert everything.status_code == 200
    rows: list[dict[str, Any]] = everything.json()
    assert {row["channel"] for row in rows} == {"whatsapp", "telegram"}
    whatsapp_row = next(row for row in rows if row["channel"] == "whatsapp")
    assert whatsapp_row["contact_name"] == "Нино"
    assert whatsapp_row["contact_phone_number"] == "+995555123456"
    assert whatsapp_row["message_count"] == 2
    assert whatsapp_row["language"] == "ru"
    assert whatsapp_row["last_message_text"].endswith("Да, есть.")
    assert len(with_sandbox.json()) == 3
    assert [row["channel"] for row in telegram.json()] == ["telegram"]


def test_conversation_card_shows_tool_calls_and_is_audited() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khinkali"}'),
            say("Хинкали — 1,20 лари."),
        )
    )
    reply = world.send("Сколько стоят хинкали?")
    client = cabinet(world)

    card = client.get(
        f"/v1/businesses/{world.business.id}/conversations/{reply.conversation_id}",
        headers=bearer("staff"),
    )

    assert card.status_code == 200
    body: dict[str, Any] = card.json()
    assert body["conversation"]["id"] == str(reply.conversation_id)
    assert [message["direction"] for message in body["messages"]] == [
        "inbound",
        "outbound",
    ]
    tool_call = body["messages"][1]["tool_calls"][0]
    assert tool_call["tool_name"] == "get_price"
    assert '"price":"1.20"' in tool_call["result_json"]
    assert body["messages"][1]["model_id"] == "scripted"
    audit = world.audit_log_repo.list_by_business(world.business.id)
    assert [(entry.action, entry.entity, entry.actor_id) for entry in audit] == [
        (AuditAction.VIEW, "conversation", world.staff_id)
    ]
    assert audit[0].entity_id == str(reply.conversation_id)
    assert audit[0].ip_address == "testclient"


def test_phone_conversation_card_shows_the_call_transcript_and_recording() -> None:
    world = build_world(scripted(say("Да, есть.")))
    reply = world.send("Есть столик на вечер?", channel=ChannelKind.PHONE)
    call = CallDocument(
        business_id=world.business.id,
        conversation_id=reply.conversation_id,
        from_phone_number=E164PhoneNumber("+995555123456"),
        to_phone_number=E164PhoneNumber("+995322000000"),
        started_at=Microseconds(1_790_855_000_000_000),
        duration_seconds=CallDurationSeconds(95),
        recording_path=RecordingStoragePath("elevenlabs/conversations/conv_1"),
        transcript=CallTranscriptText(
            "[00:00] assistant: Здравствуйте!\n[00:04] customer: Есть столик?"
        ),
        provider_call_id=ProviderCallId("conv_1"),
        outcome=CallOutcome.INFORMATION,
    )
    world.call_repo.save(call)
    other_call = call.model_copy(
        update={
            "id": CallId(),
            "conversation_id": None,
            "provider_call_id": ProviderCallId("x"),
        }
    )
    world.call_repo.save(other_call)

    card = cabinet(world).get(
        f"/v1/businesses/{world.business.id}/conversations/{reply.conversation_id}",
        headers=bearer("owner"),
    )

    assert card.status_code == 200
    [shown] = card.json()["calls"]
    assert shown["id"] == str(call.id)
    assert shown["duration_seconds"] == 95
    assert shown["outcome"] == "information"
    assert shown["transcript"].endswith("customer: Есть столик?")
    assert shown["recording_path"] == "elevenlabs/conversations/conv_1"
    audit = world.audit_log_repo.list_by_business(world.business.id)
    assert [(entry.entity, entry.entity_id) for entry in audit] == [
        ("conversation", str(reply.conversation_id)),
        ("call", str(call.id)),
    ]


def test_owners_and_staff_rate_a_conversation_good_or_bad() -> None:
    world = build_world(scripted(say("Да, есть.")))
    reply = world.send("Есть столик?")
    client = cabinet(world)
    url = (
        f"/v1/businesses/{world.business.id}/conversations/"
        f"{reply.conversation_id}/rating"
    )

    bad = client.put(url, json={"rating": "bad"}, headers=bearer("staff"))
    feed = client.get(
        f"/v1/businesses/{world.business.id}/conversations", headers=bearer("owner")
    )
    stored = world.conversations()[0]
    cleared = client.put(url, json={"rating": None}, headers=bearer("owner"))
    invalid = client.put(url, json={"rating": "meh"}, headers=bearer("owner"))
    stranger = client.put(url, json={"rating": "good"}, headers=bearer("stranger"))

    assert bad.status_code == 200, bad.text
    assert bad.json()["rating"] == "bad"
    assert feed.json()[0]["rating"] == "bad"
    assert stored.rated_by == world.staff_id
    assert stored.rated_at is not None
    assert cleared.json()["rating"] is None
    assert world.conversations()[0].rated_by is None
    assert invalid.status_code == 422
    assert stranger.status_code == 404


def test_feed_errors_map_to_http_status_codes() -> None:
    world = build_world(scripted(say("Hi")))
    reply = world.send("Hi")
    client = cabinet(world)
    base_url = f"/v1/businesses/{world.business.id}/conversations"

    responses = {
        "no token": client.get(base_url),
        "stranger": client.get(base_url, headers=bearer("stranger")),
        "bad channel": client.get(f"{base_url}?channel=fax", headers=bearer("owner")),
        "bad flag": client.get(
            f"{base_url}?include_sandbox=maybe", headers=bearer("owner")
        ),
        "malformed id": client.get(f"{base_url}/abc", headers=bearer("owner")),
        "unknown id": client.get(
            f"{base_url}/{ConversationId()}", headers=bearer("owner")
        ),
        "foreign card": client.get(
            f"/v1/businesses/{world.business.id}/conversations/{reply.conversation_id}",
            headers=bearer("stranger"),
        ),
    }

    assert {name: response.status_code for name, response in responses.items()} == {
        "no token": 401,
        "stranger": 404,
        "bad channel": 422,
        "bad flag": 422,
        "malformed id": 404,
        "unknown id": 404,
        "foreign card": 404,
    }
    assert world.audit_log_repo.list_by_business(world.business.id) == []


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
        scripted(say("published"), say("draft two"), say("other tab")),
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

    newest_ready = client.post(url, json={"text": "Hi"}, headers=bearer("staff"))
    chosen_draft = client.post(
        url,
        json={"text": "Hi", "assistant_version_id": str(draft.id)},
        headers=bearer("staff"),
    )
    other_tab = client.post(
        url,
        json={"text": "Hi", "session_key": "tab-2"},
        headers=bearer("staff"),
    )

    assert newest_ready.status_code == 200
    assert (
        len(
            {
                newest_ready.json()["conversation_id"],
                chosen_draft.json()["conversation_id"],
                other_tab.json()["conversation_id"],
            }
        )
        == 3
    )
    conversations = {
        str(conversation.id): conversation for conversation in world.conversations()
    }
    assert conversations[
        newest_ready.json()["conversation_id"]
    ].assistant_version_id == (world.version.id)
    assert conversations[
        chosen_draft.json()["conversation_id"]
    ].assistant_version_id == (draft.id)


def test_test_chat_errors() -> None:
    world = build_world(scripted(say("x")), is_published=False)
    world.version.status = AssistantVersionStatus.TESTS_FAILED
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
