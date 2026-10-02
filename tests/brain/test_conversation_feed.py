"""The conversation feed and card: filters, tool calls, calls, ratings and audit."""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import CallOutcome
from app.schemas.domain.conversations import CallDocument
from app.schemas.typings.conversations.constrained_integers import CallDurationSeconds
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.conversations.strings import (
    CallTranscriptText,
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from tests.brain.brain_world import build_world
from tests.brain.cabinet_http import bearer
from tests.brain.conversation_feed_helpers import cabinet, seed_conversations
from tests.brain.scripted_turns import call_tool, say, scripted


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
    rows: list[dict[str, Any]] = everything.json()["items"]
    assert everything.json()["next_cursor"] is None
    assert {row["channel"] for row in rows} == {"whatsapp", "telegram"}
    whatsapp_row = next(row for row in rows if row["channel"] == "whatsapp")
    assert whatsapp_row["contact_name"] == "Нино"
    assert whatsapp_row["contact_phone_number"] == "+995555123456"
    assert whatsapp_row["message_count"] == 2
    assert whatsapp_row["customer_message_count"] == 1
    assert whatsapp_row["last_message_author"] == "assistant"
    assert whatsapp_row["language"] == "ru"
    assert whatsapp_row["last_message_text"].endswith("Да, есть.")
    assert "messages" not in whatsapp_row
    assert len(with_sandbox.json()["items"]) == 3
    assert [row["channel"] for row in telegram.json()["items"]] == ["telegram"]


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
    assert feed.json()["items"][0]["rating"] == "bad"
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


def test_feed_and_its_search_are_audited_as_a_view_of_conversations() -> None:
    world = build_world(scripted(say("Да, есть.")))
    world.send("Здравствуйте, есть столик?", name="Нино")
    client = cabinet(world)
    base_url = f"/v1/businesses/{world.business.id}/conversations"

    plain = client.get(base_url, headers=bearer("owner"))
    searched = client.get(f"{base_url}?search=555123456", headers=bearer("staff"))

    assert plain.status_code == 200 and searched.status_code == 200
    assert searched.json()["items"][0]["contact_phone_number"] == "+995555123456"
    audit = world.audit_log_repo.list_by_business(world.business.id)
    assert [
        (entry.action, entry.entity, entry.entity_id, entry.actor_id, entry.ip_address)
        for entry in audit
    ] == [
        (AuditAction.VIEW, "conversation", None, world.owner_id, "testclient"),
        (AuditAction.VIEW, "conversation", None, world.staff_id, "testclient"),
    ]
