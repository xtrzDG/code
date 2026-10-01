import json
from dataclasses import dataclass
from typing import Any

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.billing import PlanKey, UsageKind
from app.schemas.constants.bookings import BookingStatus, LeadType
from app.schemas.constants.businesses import BusinessStatus, Weekday
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.profiles import BusinessProfileDocument, OpeningInterval
from app.schemas.dto.channels import DisableChannelCommand
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText, VoiceAgentId
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import (
    derive_voice_tool_secret,
    sign_body,
)
from tests.channels.testbed import (
    ELEVENLABS_WEBHOOK_SECRET,
    GEORGIA,
    ISRAEL,
    TELEGRAM_BOT_TOKEN,
    ChannelsTestbed,
    CountrySetup,
    HttpResponse,
    build_settings,
    sign_elevenlabs,
    telegram_ok,
    to_json_bytes,
)

ASSISTANT_LINE: str = "+995322000000"
CALLER: str = "+995599123456"
# 2026-10-03 15:30 UTC (19:30 in Tbilisi).
BOOKING_STARTS_AT: int = 1_791_041_400


def tool_secret(business_id: BusinessId) -> str:
    return str(
        derive_voice_tool_secret(PlatformSecret(ELEVENLABS_WEBHOOK_SECRET), business_id)
    )


@dataclass
class VoiceSetup:
    testbed: ChannelsTestbed
    business: BusinessDocument
    contact: ContactDocument
    conversation: ConversationDocument


def build_voice_setup(
    country: CountrySetup = GEORGIA,
    settings: Any = None,
    conversation_language: str | None = "ka",
) -> VoiceSetup:
    testbed = ChannelsTestbed(settings)
    owner_id = testbed.add_user("owner")
    business = testbed.add_business(owner_id, country=country)
    testbed.add_channel(business.id, ChannelKind.PHONE, ASSISTANT_LINE)
    version = AssistantVersionDocument(
        business_id=business.id,
        version_number=AssistantVersionNumber(1),
        niche_key=NicheKey.ENTERTAINMENT,
        model_id=LlmModelId("gpt-5-mini"),
        prompt_text=SystemPromptText("Prompt"),
        tools=[AssistantToolName.CREATE_BOOKING],
        languages=business.languages,
        default_language=business.default_language,
        is_voice_enabled=True,
        facts=[],
        profile_revision=Microseconds(1),
        voice_agent_id=VoiceAgentId("agent_1"),
    )
    testbed.assistant_version_repo.save(version)
    # A live business whose published version answers the phone.
    business.status = BusinessStatus.LIVE
    business.published_assistant_version_id = version.id
    testbed.business_repo.save(business)
    contact = ContactDocument(
        business_id=business.id,
        phone_number=E164PhoneNumber(CALLER),
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.PHONE, channel_user_id=ChannelUserId(CALLER)
            ),
            ChannelIdentity(
                channel=ChannelKind.TELEGRAM, channel_user_id=ChannelUserId("555000111")
            ),
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP,
                channel_user_id=ChannelUserId("995599123456"),
            ),
        ],
    )
    testbed.contact_repo.save(contact)
    conversation = ConversationDocument(
        business_id=business.id,
        contact_id=contact.id,
        assistant_version_id=version.id,
        channel=ChannelKind.PHONE,
        channel_user_id=ChannelUserId("conv_1"),
        language=None
        if conversation_language is None
        else LanguageTag(conversation_language),
        last_message_at=testbed.clock.now_microseconds(),
    )
    testbed.conversation_repo.save(conversation)
    return VoiceSetup(testbed, business, contact, conversation)


def add_booking(setup: VoiceSetup, party_size: int = 4) -> BookingDocument:
    booking = BookingDocument(
        business_id=setup.business.id,
        resource_id=ResourceId(),
        contact_id=setup.contact.id,
        conversation_id=setup.conversation.id,
        starts_at=BookingStartsAtUnixSeconds(BOOKING_STARTS_AT),
        ends_at=BookingEndsAtUnixSeconds(BOOKING_STARTS_AT + 3600),
        party_size=PartySize(party_size),
        source_channel=ChannelKind.PHONE,
    )
    setup.testbed.booking_repo.save(booking)
    return booking


def post_call_payload(
    conversation_id: str = "conv_1",
    agent_number: str | None = "995322000000",
    external_number: str | None = "+995 599 12 34 56",
    duration: int = 95,
    tool_names: tuple[str, ...] = (),
    caller_spoke: bool = True,
    event_type: str = "post_call_transcription",
    agent_id: str = "agent_1",
    metadata_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    transcript: list[dict[str, Any]] = [
        {
            "role": "agent",
            "message": "გამარჯობა! AI ასისტენტი.",
            "time_in_call_secs": 0,
            "tool_calls": [
                {
                    "request_id": f"r{index}",
                    "tool_name": name,
                    "params_as_json": "{}",
                    "tool_has_been_called": True,
                }
                for index, name in enumerate(tool_names)
            ],
        }
    ]
    if caller_spoke:
        transcript.append(
            {"role": "user", "message": "მაგიდა ოთხისთვის", "time_in_call_secs": 65}
        )
    phone_call: dict[str, Any] = {
        "type": "sip_trunking",
        "direction": "inbound",
        "phone_number_id": "pn_1",
        "call_sid": "sid",
    }
    if agent_number is not None:
        phone_call["agent_number"] = agent_number
    if external_number is not None:
        phone_call["external_number"] = external_number
    metadata: dict[str, Any] = {
        "start_time_unix_secs": 1_790_855_000,
        "call_duration_secs": duration,
        "cost": 296,
        "cost_fiat": 0.1523,
        "main_language": "ka",
        "phone_call": phone_call,
        **(metadata_extra or {}),
    }
    return {
        "type": event_type,
        "event_timestamp": 1_790_855_100,
        "data": {
            "agent_id": agent_id,
            "conversation_id": conversation_id,
            "status": "done",
            "transcript": transcript,
            "metadata": metadata,
            "has_audio": True,
        },
    }


def post_call(
    setup: VoiceSetup,
    payload: dict[str, Any],
    signature: str | None = "valid",
    signed_at: int | None = None,
) -> HttpResponse:
    body: bytes = to_json_bytes(payload)
    headers: dict[str, str] = {}
    if signature == "valid":
        headers["ElevenLabs-Signature"] = sign_elevenlabs(
            body, signed_at or setup.testbed.clock.now_seconds()
        )
    elif signature is not None:
        headers["ElevenLabs-Signature"] = signature
    return setup.testbed.build_http_client().post(
        "/v1/voice/webhooks/post-call", content=body, headers=headers
    )


def stored_calls(setup: VoiceSetup) -> list[CallDocument]:
    return setup.testbed.call_repo.list_by_business(setup.business.id)


class TestVoiceToolWebhook:
    def call_tool(
        self,
        setup: VoiceSetup,
        tool_name: str,
        body: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        default_headers: dict[str, str] = {
            "X-Assistant-Business-Id": str(setup.business.id),
            "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
        }
        return setup.testbed.build_http_client().post(
            f"/v1/voice/tools/{tool_name}",
            content=to_json_bytes(body),
            headers=default_headers if headers is None else headers,
        )

    def test_tool_call_runs_with_the_business_from_the_credentials(self) -> None:
        setup = build_voice_setup(country=ISRAEL)
        arguments = {"name": "דנה", "party_size": 2, "starts_at": "2026-10-03T19:30"}

        response = self.call_tool(
            setup,
            "create_booking",
            {
                "arguments": arguments,
                "conversation_id": "conv_9",
                "caller_id": "050-234-5678",
                "language": "he",
                "business_id": "business_of_someone_else",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"ok": True, "tool": "create_booking"}
        [request] = setup.testbed.voice_tool_orchestrator.requests
        assert request.business_id == setup.business.id
        assert request.provider_call_id == "conv_9"
        assert request.caller_phone_number == "+972502345678"
        assert request.tool_name is AssistantToolName.CREATE_BOOKING
        assert request.language == "he"
        assert json.loads(request.input_json) == arguments

    def test_body_signature_is_an_alternative_to_the_secret(self) -> None:
        setup = build_voice_setup()
        body = {"arguments": {"query": "parking"}, "conversation_id": "conv_1"}
        raw: bytes = to_json_bytes(body)
        signature = "sha256=" + sign_body(tool_secret(setup.business.id), raw)

        response = setup.testbed.build_http_client().post(
            "/v1/voice/tools/search_knowledge",
            content=raw,
            headers={
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Signature": signature,
            },
        )

        assert response.status_code == 200
        [request] = setup.testbed.voice_tool_orchestrator.requests
        assert request.caller_phone_number is None
        assert request.language is None

    def test_flat_bodies_and_withheld_numbers(self) -> None:
        setup = build_voice_setup()

        self.call_tool(
            setup,
            "get_price",
            {
                "item_name": "VR hour",
                "conversation_id": "conv_1",
                "caller_id": "anonymous",
            },
        )

        [request] = setup.testbed.voice_tool_orchestrator.requests
        assert json.loads(request.input_json) == {"item_name": "VR hour"}
        assert request.caller_phone_number is None

    @pytest.mark.parametrize("variant", ["missing", "wrong", "other_business", "no_id"])
    def test_unauthenticated_tool_calls_are_refused(self, variant: str) -> None:
        setup = build_voice_setup()
        other = BusinessId()
        headers: dict[str, str] = {
            "missing": {"X-Assistant-Business-Id": str(setup.business.id)},
            "wrong": {
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": "0" * 64,
            },
            "other_business": {
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": tool_secret(other),
            },
            "no_id": {"X-Assistant-Tool-Secret": tool_secret(setup.business.id)},
        }[variant]

        response = self.call_tool(
            setup, "get_price", {"arguments": {}, "conversation_id": "c"}, headers
        )

        assert response.status_code == 401
        assert setup.testbed.voice_tool_orchestrator.requests == []

    def test_unknown_tools_and_malformed_bodies(self) -> None:
        setup = build_voice_setup()

        unknown = self.call_tool(setup, "delete_everything", {"conversation_id": "c"})
        no_call = self.call_tool(setup, "get_price", {"arguments": {}})
        bad_arguments = self.call_tool(
            setup, "get_price", {"arguments": [1, 2], "conversation_id": "c"}
        )

        assert unknown.status_code == 404
        assert no_call.status_code == 422
        assert bad_arguments.status_code == 422

    def test_deleted_business_is_not_found(self) -> None:
        setup = build_voice_setup()
        ghost = BusinessId()

        response = self.call_tool(
            setup,
            "get_price",
            {"arguments": {}, "conversation_id": "c"},
            {
                "X-Assistant-Business-Id": str(ghost),
                "X-Assistant-Tool-Secret": tool_secret(ghost),
            },
        )

        assert response.status_code == 404

    def test_unconfigured_voice_webhooks_refuse_everything(self) -> None:
        setup = build_voice_setup(settings=build_settings(ELEVENLABS_WEBHOOK_SECRET=""))

        assert (
            self.call_tool(setup, "get_price", {"conversation_id": "c"}).status_code
            == 401
        )


class TestCallInitiation:
    def test_greeting_in_the_default_language(self) -> None:
        setup = build_voice_setup()

        response = setup.testbed.build_http_client().post(
            "/v1/voice/webhooks/conversation-initiation",
            content=to_json_bytes(
                {
                    "caller_id": CALLER,
                    "agent_id": "agent_1",
                    "called_number": ASSISTANT_LINE,
                }
            ),
            headers={
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "first_message": "[ka] AI assistant of Funicular VR.",
                    "language": "ka",
                }
            },
            # No opening hours in the profile: never put through to staff.
            "dynamic_variables": {"is_open_now": "no"},
        }
        [greeting_request] = setup.testbed.call_greeting.requests
        assert greeting_request.business_id == setup.business.id
        assert greeting_request.language is None

    @pytest.mark.parametrize(
        "switch_off",
        ["pause", "chat_plan", "version_without_voice", "number_disconnected"],
    )
    def test_no_call_is_answered_while_the_phone_assistant_is_off(
        self, switch_off: str
    ) -> None:
        setup = build_voice_setup()
        testbed = setup.testbed
        if switch_off == "pause":
            setup.business.status = BusinessStatus.PAUSED
        elif switch_off == "chat_plan":
            setup.business.plan_key = PlanKey.CHAT
        elif switch_off == "version_without_voice":
            version = testbed.assistant_version_repo.get(
                setup.business.id, setup.conversation.assistant_version_id
            )
            assert version is not None
            version.is_voice_enabled = False
            testbed.assistant_version_repo.save(version)
        else:
            for channel in testbed.channel_repo.list_by_business(setup.business.id):
                channel.status = ChannelStatus.DISABLED
                testbed.channel_repo.save(channel)

        testbed.business_repo.save(setup.business)
        response = testbed.build_http_client().post(
            "/v1/voice/webhooks/conversation-initiation",
            content=to_json_bytes({"caller_id": CALLER, "agent_id": "agent_1"}),
            headers={
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
            },
        )

        assert response.status_code == 409, response.text
        assert testbed.call_greeting.requests == []

    @pytest.mark.parametrize(
        ("opens", "closes", "expected"),
        [(0, 1440, "yes"), (0, 1, "no")],
    )
    def test_the_agent_learns_whether_the_business_is_open_now(
        self, opens: int, closes: int, expected: str
    ) -> None:
        setup = build_voice_setup()
        setup.testbed.profile_repo.save(
            BusinessProfileDocument(
                business_id=setup.business.id,
                niche_key=NicheKey.ENTERTAINMENT,
                answers_language=LanguageTag("ka"),
                hours=[
                    OpeningInterval(
                        weekday=weekday,
                        opens_at=OpeningMinuteOfDay(opens),
                        closes_at=ClosingMinuteOfDay(closes),
                    )
                    for weekday in Weekday
                ],
            )
        )

        response = setup.testbed.build_http_client().post(
            "/v1/voice/webhooks/conversation-initiation",
            content=to_json_bytes({"caller_id": CALLER, "agent_id": "agent_1"}),
            headers={
                "X-Assistant-Business-Id": str(setup.business.id),
                "X-Assistant-Tool-Secret": tool_secret(setup.business.id),
            },
        )

        assert response.json()["dynamic_variables"] == {"is_open_now": expected}

    def test_initiation_needs_the_business_secret(self) -> None:
        setup = build_voice_setup()

        response = setup.testbed.build_http_client().post(
            "/v1/voice/webhooks/conversation-initiation",
            content=b"{}",
            headers={"X-Assistant-Business-Id": str(setup.business.id)},
        )

        assert response.status_code == 401


class TestPostCallWebhook:
    def test_booking_call_is_stored_billed_and_confirmed(self) -> None:
        setup = build_voice_setup()
        setup.testbed.add_channel(
            setup.business.id,
            ChannelKind.TELEGRAM,
            "funicular_vr_bot",
            TELEGRAM_BOT_TOKEN,
        )
        setup.testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", telegram_ok({})
        )
        add_booking(setup)

        response = post_call(setup, post_call_payload(tool_names=("create_booking",)))

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "recorded"
        assert body["outcome"] == "booking"
        assert body["is_confirmation_sent"] is True
        [call] = stored_calls(setup)
        assert str(call.id) == body["call_id"]
        assert call.conversation_id == setup.conversation.id
        assert call.from_phone_number == CALLER
        assert call.to_phone_number == ASSISTANT_LINE
        assert call.started_at == 1_790_855_000_000_000
        assert call.duration_seconds == 95
        assert call.cost_micro_usd == 152_300
        assert call.recording_path == "elevenlabs/conversations/conv_1"
        assert call.transcript == (
            "[00:00] assistant: გამარჯობა! AI ასისტენტი.\n"
            "[01:05] customer: მაგიდა ოთხისთვის"
        )
        [usage] = setup.testbed.usage_event_repo.list_by_business_between(
            setup.business.id, Microseconds(0), Microseconds(2**62)
        )
        assert usage.kind is UsageKind.VOICE_SECONDS
        assert usage.quantity == 95
        assert usage.cost_micro_usd == 152_300
        assert ("create", "call") in setup.testbed.audit_actions(setup.business.id)
        [sent] = setup.testbed.telegram_transport.requests_to("/sendMessage")
        assert sent.json()["chat_id"] == "555000111"
        text: str = sent.json()["text"]
        assert text.startswith("Funicular VR: თქვენი ჯავშანი დადასტურებულია")
        assert "19:30" in text
        assert "სტუმრები: 4." in text

    def test_confirmation_falls_back_to_the_next_messenger(self) -> None:
        setup = build_voice_setup(conversation_language="ru")
        setup.testbed.add_channel(
            setup.business.id,
            ChannelKind.TELEGRAM,
            "funicular_vr_bot",
            TELEGRAM_BOT_TOKEN,
        )
        setup.testbed.add_channel(
            setup.business.id, ChannelKind.WHATSAPP, "106540352242922"
        )
        setup.testbed.telegram_transport.respond(
            "POST",
            r"/sendMessage$",
            {"ok": False, "error_code": 403, "description": "blocked"},
            status_code=403,
        )
        setup.testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})
        add_booking(setup, party_size=1)

        body = post_call(setup, post_call_payload()).json()

        assert body["is_confirmation_sent"] is True
        [whatsapp] = setup.testbed.meta_transport.requests
        message: str = whatsapp.json()["text"]["body"]
        assert message.startswith("Funicular VR: ваша бронь на ")
        assert "Гостей" not in message

    def test_no_reachable_messenger_means_no_confirmation(self) -> None:
        setup = build_voice_setup()
        add_booking(setup)

        body = post_call(setup, post_call_payload()).json()

        assert body["outcome"] == "booking"
        assert body["is_confirmation_sent"] is False

    def test_cancelled_bookings_do_not_count(self) -> None:
        setup = build_voice_setup()
        booking = add_booking(setup)
        booking.status = BookingStatus.CANCELLED
        setup.testbed.booking_repo.save(booking)

        assert post_call(setup, post_call_payload()).json()["outcome"] == "information"

    def test_lead_handoff_and_unanswered_outcomes(self) -> None:
        lead_setup = build_voice_setup()
        lead_setup.testbed.lead_repo.save(
            LeadDocument(
                business_id=lead_setup.business.id,
                contact_id=lead_setup.contact.id,
                conversation_id=lead_setup.conversation.id,
                lead_type=LeadType.BANQUET,
                details=LeadDetails("Banquet for 40"),
                source_channel=ChannelKind.PHONE,
            )
        )
        handoff_setup = build_voice_setup()
        handoff_setup.testbed.handoff_repo.save(
            HandoffDocument(
                business_id=handoff_setup.business.id,
                conversation_id=handoff_setup.conversation.id,
                contact_id=handoff_setup.contact.id,
                reason=HandoffReason.COMPLAINT,
                summary=HandoffSummary("Complaint"),
            )
        )
        question_setup = build_voice_setup()

        assert post_call(lead_setup, post_call_payload()).json()["outcome"] == "lead"
        assert (
            post_call(handoff_setup, post_call_payload()).json()["outcome"] == "handoff"
        )
        assert (
            post_call(
                question_setup,
                post_call_payload(tool_names=("record_unanswered_question", "unknown")),
            ).json()["outcome"]
            == "unanswered_question"
        )

    def test_information_and_abandoned_calls(self) -> None:
        setup = build_voice_setup()

        short = post_call(setup, post_call_payload("conv_short", duration=4)).json()
        silent = post_call(
            setup, post_call_payload("conv_silent", caller_spoke=False)
        ).json()
        informative = post_call(setup, post_call_payload("conv_info")).json()

        assert short["outcome"] == "abandoned"
        assert silent["outcome"] == "abandoned"
        assert informative["outcome"] == "information"
        assert all(call.conversation_id is None for call in stored_calls(setup)[:2])

    def test_repeated_webhook_is_not_billed_twice(self) -> None:
        setup = build_voice_setup()

        first = post_call(setup, post_call_payload()).json()
        second = post_call(setup, post_call_payload(duration=96)).json()

        assert first["status"] == "recorded"
        assert second["status"] == "duplicate"
        assert first["call_id"] == second["call_id"]
        [call] = stored_calls(setup)
        assert call.duration_seconds == 96
        assert (
            len(
                setup.testbed.usage_event_repo.list_by_business_between(
                    setup.business.id, Microseconds(0), Microseconds(2**62)
                )
            )
            == 1
        )

    @pytest.mark.parametrize(
        "variant", ["missing", "wrong_secret", "tampered", "stale", "future", "garbage"]
    )
    def test_signature_is_required(self, variant: str) -> None:
        setup = build_voice_setup()
        payload = post_call_payload()
        now: int = setup.testbed.clock.now_seconds()
        body: bytes = to_json_bytes(payload)
        signature: str | None = {
            "missing": None,
            "wrong_secret": sign_elevenlabs(body, now, secret="another"),
            "tampered": sign_elevenlabs(body + b" ", now),
            "stale": sign_elevenlabs(body, now - 31 * 60),
            "future": sign_elevenlabs(body, now + 31 * 60),
            "garbage": "t=abc,v0=",
        }[variant]

        response = post_call(setup, payload, signature=signature)

        assert response.status_code == 401
        assert stored_calls(setup) == []

    def test_slightly_old_signatures_are_accepted(self) -> None:
        setup = build_voice_setup()
        response = post_call(
            setup,
            post_call_payload(),
            signed_at=setup.testbed.clock.now_seconds() - 29 * 60,
        )
        assert response.json()["status"] == "recorded"

    def test_other_events_and_unknown_numbers_are_ignored(self) -> None:
        setup = build_voice_setup()

        audio = post_call(setup, post_call_payload(event_type="post_call_audio"))
        unknown_line = post_call(setup, post_call_payload(agent_number="+48221234567"))
        no_line = post_call(setup, post_call_payload(agent_number=None))
        foreign_agent = post_call(setup, post_call_payload(agent_id="agent_of_others"))

        for response in (audio, unknown_line, no_line, foreign_agent):
            assert response.status_code == 200
            assert response.json()["status"] == "ignored"

        assert stored_calls(setup) == []

    def test_a_call_on_a_number_that_broke_is_still_stored_and_metered(
        self,
    ) -> None:
        setup = build_voice_setup()
        for channel in setup.testbed.channel_repo.list_by_business(setup.business.id):
            channel.status = ChannelStatus.ERROR
            setup.testbed.channel_repo.save(channel)

        response = post_call(setup, post_call_payload())

        assert response.json()["status"] == "recorded"
        assert len(stored_calls(setup)) == 1
        [usage] = setup.testbed.usage_event_repo.list_by_business_between(
            setup.business.id, Microseconds(0), Microseconds(2**62)
        )
        assert usage.kind is UsageKind.VOICE_SECONDS

    def test_minutes_after_a_transfer_to_staff_are_metered(self) -> None:
        setup = build_voice_setup()
        payload = post_call_payload()
        payload["data"]["transcript"].append(
            {
                "role": "agent",
                "message": "Connecting you to a colleague.",
                "time_in_call_secs": 35,
                "tool_calls": [{"tool_name": "transfer_to_number"}],
            }
        )

        response = post_call(setup, payload)

        assert response.json()["status"] == "recorded"
        usage = setup.testbed.usage_event_repo.list_by_business_between(
            setup.business.id, Microseconds(0), Microseconds(2**62)
        )
        assert {(event.kind, int(event.quantity)) for event in usage} == {
            (UsageKind.VOICE_SECONDS, 95),
            (UsageKind.TRANSFER_SECONDS, 60),
        }

    def test_turning_the_phone_number_off_removes_the_voice_agent(self) -> None:
        setup = build_voice_setup()
        owner_id = setup.business.members[0].user_id

        setup.testbed.disable_channel.run(
            DisableChannelCommand(
                user_id=owner_id,
                business_id=setup.business.id,
                channel=ChannelKind.PHONE,
            )
        )

        assert setup.testbed.voice_agent_removals == [setup.business.id]

    def test_malformed_reports_are_rejected(self) -> None:
        setup = build_voice_setup()
        payload = post_call_payload()
        del payload["data"]["conversation_id"]

        assert post_call(setup, payload).status_code == 422
        assert post_call(setup, {"type": "post_call_transcription"}).status_code == 422

    def test_called_number_from_dynamic_variables_and_cost_fallback(self) -> None:
        setup = build_voice_setup()
        payload = post_call_payload(
            agent_number=None,
            external_number=None,
            metadata_extra={
                "cost_fiat": None,
                "charging": {"llm_price": 0.01, "platform_price": 0.05},
            },
        )
        payload["data"]["conversation_initiation_client_data"] = {
            "dynamic_variables": {
                "system__called_number": ASSISTANT_LINE,
                "system__caller_id": "+1 202 555 0123",
            }
        }

        assert post_call(setup, payload).json()["status"] == "recorded"
        [call] = stored_calls(setup)
        assert call.from_phone_number == "+12025550123"
        assert call.cost_micro_usd == 60_000

    def test_tenant_isolation_between_assistant_lines(self) -> None:
        first = build_voice_setup()
        testbed = first.testbed
        other_owner = testbed.add_user("other")
        other_business = testbed.add_business(other_owner, name="Other")
        testbed.add_channel(other_business.id, ChannelKind.PHONE, "+995322111111")

        post_call(first, post_call_payload(agent_number="+995322111111"))

        assert testbed.call_repo.list_by_business(first.business.id) == []
        [other_call] = testbed.call_repo.list_by_business(other_business.id)
        assert other_call.conversation_id is None
