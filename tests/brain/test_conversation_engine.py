import json
from datetime import timedelta
from typing import Any

import pytest

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import (
    ConversationStatus,
    LlmTurnRole,
    MessageAuthor,
    ReplyGuardVerdict,
)
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.dto.bookings import CancelBookingCommand, CreateBookingCommand
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmResponse,
    LlmToolResult,
)
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
    LlmRefusedError,
    NotFoundError,
)
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.business_setups import ARMENIA, BRAZIL, ISRAEL
from tests.brain.scripted_turns import call_tool, say, scripted


class CountingLlmAdapter(LlmAdapterContract):
    """Scripted model that reports token usage like a real provider."""

    def __init__(
        self,
        inner: ScriptedLlmAdapter,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self.inner: ScriptedLlmAdapter = inner
        self._input_tokens: int = input_tokens
        self._output_tokens: int = output_tokens

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self.inner.build_user_text_turn(text)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return self.inner.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        response: LlmResponse = self.inner.complete(request)
        return response.model_copy(
            update={
                "input_tokens": LlmTokenCount(self._input_tokens),
                "output_tokens": LlmTokenCount(self._output_tokens),
            }
        )


def user_turn_text(payload: LlmProviderPayload) -> str:
    content: list[dict[str, Any]] = json.loads(payload)["content"]
    return "".join(block.get("text", "") for block in content)


def requests_of(world: BrainWorld) -> list[LlmRequest]:
    assert isinstance(world.llm, ScriptedLlmAdapter)
    return world.llm.requests


def test_first_reply_starts_with_the_localized_disclosure_only_once() -> None:
    world = build_world(
        scripted(say("რით შემიძლია დაგეხმაროთ?"), say("ხვალ 12:00-დან ვართ ღია."))
    )

    first = world.send("გამარჯობა!")
    second = world.send("ხვალ რომელ საათზე იხსნებით?")

    assert first.text == (
        "გამარჯობა! მე ვარ Sakhli-ის AI-ასისტენტი.\nრით შემიძლია დაგეხმაროთ?"
    )
    assert first.language == "ka"
    assert second.text == "ხვალ 12:00-დან ვართ ღია."
    assert first.conversation_id == second.conversation_id
    first_turn_text = user_turn_text(requests_of(world)[0].transcript[0])
    second_turn_text = user_turn_text(requests_of(world)[1].transcript[-1])
    assert "Local time at the business: Thursday 2026-10-01 14:00 (Asia/Tbilisi)." in (
        first_turn_text
    )
    assert "Next days: Fri 2026-10-02, Sat 2026-10-03" in first_turn_text
    assert "Channel: whatsapp." in first_turn_text
    assert "Customer: phone +995555123456." in first_turn_text
    assert "first reply in this conversation" in first_turn_text
    assert first_turn_text.endswith("[Customer message]\nგამარჯობა!")
    assert "first reply" not in second_turn_text


@pytest.mark.parametrize(
    ("setup", "text", "language", "disclosure"),
    [
        (ISRAEL, "שלום, יש לכם שולחן פנוי?", "he", "שלום! אני עוזר ה-AI של Beit Kafe."),
        (
            ISRAEL,
            "مرحبا، هل لديكم طاولة؟",
            "ar",
            "مرحبًا! أنا مساعد الذكاء الاصطناعي لدى Beit Kafe.",
        ),
        (
            ISRAEL,
            "Привет, есть столик?",
            "ru",
            "Здравствуйте! Я AI-ассистент «Beit Kafe».",
        ),
        (
            ARMENIA,
            "Բարև, սեղան ունե՞ք",
            "hy",
            "Բարև Ձեզ։ Ես Ararat Grill-ի AI օգնականն եմ։",
        ),
        (
            BRAZIL,
            "Olá, vocês têm mesa?",
            "pt-BR",
            "Olá! Sou o assistente de IA de Cantina Sol.",
        ),
        (
            BRAZIL,
            "Hola, ¿tienen mesa?",
            "es",
            "¡Hola! Soy el asistente de IA de Cantina Sol.",
        ),
    ],
)
def test_language_is_detected_among_the_version_languages(
    setup: Any,
    text: str,
    language: str,
    disclosure: str,
) -> None:
    world = build_world(scripted(say("…")), setup)

    reply = world.send(text, phone=None)

    assert reply.language == language
    assert reply.text is not None
    assert reply.text.startswith(disclosure)
    stored = world.messages(reply.conversation_id)
    assert [message.language for message in stored] == [language, language]
    assert world.contacts()[0].language == language


def test_booking_flow_runs_tool_rounds_and_stores_everything() -> None:
    llm = CountingLlmAdapter(
        scripted(
            call_tool(
                AssistantToolName.CHECK_AVAILABILITY,
                '{"resource_type":"table","date":"2026-10-02","time":"19:30",'
                '"party_size":4,"duration_minutes":null,"nights":null}',
            ),
            call_tool(
                AssistantToolName.CREATE_BOOKING,
                '{"name":"Нино","phone":null,"resource_type":"table",'
                '"date":"2026-10-02","time":"19:30","party_size":4,'
                '"duration_minutes":null,"nights":null,"notes":null}',
            ),
            say("Готово! Столик на 4 человек 2 октября в 19:30 на имя Нино."),
        ),
        input_tokens=10_000,
        output_tokens=1_000,
    )
    world = build_world(llm)
    world.version.model_id = LlmModelId("gpt-5-mini")
    world.version_repo.save(world.version)

    reply = world.send("Хочу столик завтра на 4 человек в 19:30", name="Нино")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert len(reply.created_booking_ids) == 1
    assert reply.is_handed_off is False
    assert reply.text is not None
    assert reply.text.endswith("на имя Нино.")
    contact = world.contacts()[0]
    command = world.bookings.commands[0]
    assert isinstance(command, CreateBookingCommand)
    assert command.business_id == world.business.id
    assert command.contact_id == contact.id
    assert command.conversation_id == reply.conversation_id
    assert command.contact_phone_number == "+995555123456"
    assert command.source_channel is ChannelKind.WHATSAPP
    assert command.language == "ru"
    assert command.date == LocalDate("2026-10-02")
    assert world.availability.queries[0].business_id == world.business.id

    turns = world.turns(reply.conversation_id)
    assert [int(turn.sequence_number) for turn in turns] == [0, 1, 2, 3, 4, 5]
    assert [turn.role for turn in turns] == [
        LlmTurnRole.USER,
        LlmTurnRole.ASSISTANT,
        LlmTurnRole.USER,
        LlmTurnRole.ASSISTANT,
        LlmTurnRole.USER,
        LlmTurnRole.ASSISTANT,
    ]
    tool_results_turn = json.loads(turns[2].payload)
    assert tool_results_turn["content"][0]["type"] == "tool_result"
    assert len(llm.inner.requests) == 3
    assert len(llm.inner.requests[2].transcript) == 5
    assert [tool.name for tool in llm.inner.requests[0].tools] == list(
        AssistantToolName
    )

    outbound = world.messages(reply.conversation_id)[-1]
    assert outbound.direction is MessageDirection.OUTBOUND
    assert outbound.author is MessageAuthor.ASSISTANT
    assert [record.tool_name for record in outbound.tool_calls] == [
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
    ]
    assert outbound.model_id == "gpt-5-mini"
    assert (int(outbound.input_tokens), int(outbound.output_tokens)) == (30_000, 3_000)
    assert int(outbound.cost_micro_usd) == 30_000 * 0.25 + 3_000 * 2
    usage = {event.kind: event for event in world.usage_events()}
    assert int(usage[UsageKind.LLM_INPUT_TOKENS].quantity) == 30_000
    assert int(usage[UsageKind.LLM_INPUT_TOKENS].cost_micro_usd) == 7_500
    assert int(usage[UsageKind.LLM_OUTPUT_TOKENS].cost_micro_usd) == 6_000
    assert int(usage[UsageKind.DIALOG].quantity) == 1


def test_dialog_usage_is_counted_once_per_conversation() -> None:
    world = build_world(scripted(say("Да."), say("Конечно.")))

    world.send("Здравствуйте")
    world.send("Есть веранда?")

    assert [event.kind for event in world.usage_events()] == [UsageKind.DIALOG]


def test_transcript_is_append_only_across_messages() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khachapuri"}'),
            say("Adjarian khachapuri costs 18 GEL."),
            say("You are welcome!"),
        )
    )

    first = world.send("How much is khachapuri?")
    first_turns = [
        (turn.id, turn.payload) for turn in world.turns(first.conversation_id)
    ]
    second = world.send("Thanks!")
    all_turns = world.turns(second.conversation_id)

    assert first.conversation_id == second.conversation_id
    assert [(turn.id, turn.payload) for turn in all_turns[:4]] == first_turns
    assert [int(turn.sequence_number) for turn in all_turns] == list(range(6))
    assert requests_of(world)[2].transcript[:4] == [
        payload for _, payload in first_turns
    ]


def test_contact_and_channel_identity_are_reused_and_completed() -> None:
    world = build_world(scripted(say("Привет!"), say("Да."), say("Конечно.")))

    world.send("Привет", phone=None)
    world.send("Есть парковка?", name="Георгий", phone=None)
    world.send("Здравствуйте", channel=ChannelKind.TELEGRAM, user_id="42", phone=None)

    contacts = world.contacts()
    assert len(contacts) == 2
    whatsapp_contact = next(
        contact
        for contact in contacts
        if contact.channel_identities[0].channel is ChannelKind.WHATSAPP
    )
    assert whatsapp_contact.name == "Георгий"
    assert len(world.conversations()) == 2


def test_phone_number_links_a_new_channel_to_the_known_contact() -> None:
    world = build_world(scripted(say("Hello!"), say("Hi again!")))

    world.send("Hi", channel=ChannelKind.WHATSAPP, user_id="995555123456")
    world.send("Hi", channel=ChannelKind.TELEGRAM, user_id="777")

    contacts = world.contacts()
    assert len(contacts) == 1
    assert {identity.channel for identity in contacts[0].channel_identities} == {
        ChannelKind.WHATSAPP,
        ChannelKind.TELEGRAM,
    }


def test_model_handoff_silences_the_assistant_in_chat() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"complaint","summary":"Cold soup","urgency":"high"}',
            ),
            say("I am sorry! A colleague will contact you soon."),
        )
    )

    first = world.send("The soup was cold, I want to talk to a manager")
    second = world.send("Hello? Anyone?")

    assert first.is_handed_off is True
    assert len(first.created_handoff_ids) == 1
    assert world.handoffs()[0].reason is HandoffReason.COMPLAINT
    assert second.text is None
    assert second.is_handed_off is True
    assert second.should_end_call is False
    assert len(requests_of(world)) == 2
    stored = world.messages(second.conversation_id)
    assert stored[-1].direction is MessageDirection.INBOUND
    assert stored[-1].text == "Hello? Anyone?"
    assert world.conversations()[0].status is ConversationStatus.HANDOFF


def test_phone_caller_in_handoff_is_promised_a_call_back() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Wants a manager",'
                '"urgency":"normal"}',
            ),
            say("Соединяю с коллегой."),
        )
    )

    first = world.send(
        "Позовите менеджера", channel=ChannelKind.PHONE, user_id="call-1"
    )
    second = world.send("Алло?", channel=ChannelKind.PHONE, user_id="call-1")

    assert first.should_end_call is True
    assert first.text == "Соединяю с коллегой."
    assert second.text == (
        "Ваш запрос уже у коллеги — вам скоро перезвонят. Спасибо за звонок!"
    )
    assert second.should_end_call is True
    assert second.is_handed_off is True


def test_phone_goodbye_ends_the_call_and_phone_replies_skip_the_disclosure() -> None:
    world = build_world(scripted(say("Будем рады вас видеть!"), say("Всего доброго!")))

    first = world.send(
        "Вы работаете завтра?", channel=ChannelKind.PHONE, user_id="call-7"
    )
    second = world.send(
        "Спасибо, до свидания!", channel=ChannelKind.PHONE, user_id="call-7"
    )

    assert first.text == "Будем рады вас видеть!"
    assert first.should_end_call is False
    assert second.should_end_call is True


def test_leads_only_mode_offers_only_requests_and_handoff() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.CREATE_BOOKING,
                '{"name":"Ann","phone":null,"resource_type":null,"date":"2026-10-02",'
                '"time":"19:00","party_size":2,"duration_minutes":null,'
                '"nights":null,"notes":null}',
            ),
            call_tool(
                AssistantToolName.CREATE_LEAD,
                '{"lead_type":"other","details":"Table for 2 tomorrow at 19:00",'
                '"name":"Ann","phone":null,"requested_date":"2026-10-02",'
                '"party_size":2,"budget":null}',
            ),
            say("I passed your request for tomorrow at 19:00 to the manager."),
        )
    )
    world.business.service_mode = ServiceMode.LEADS_ONLY
    world.save_business(world.business)

    reply = world.send("Table for 2 tomorrow at 19:00 please")

    request = requests_of(world)[0]
    assert {tool.name for tool in request.tools} == {
        AssistantToolName.CREATE_LEAD,
        AssistantToolName.HANDOFF_TO_HUMAN,
        AssistantToolName.SEARCH_KNOWLEDGE,
    }
    assert "Bookings are paused" in user_turn_text(request.transcript[0])
    assert world.bookings.commands == []
    assert len(reply.created_lead_ids) == 1
    outbound = world.messages(reply.conversation_id)[-1]
    assert outbound.tool_calls[0].is_error is True
    assert "not available" in outbound.tool_calls[0].result_json


def test_contact_limit_answers_once_then_stays_silent_for_the_hour() -> None:
    world = build_world(
        scripted(say("Привет!"), say("Да."), say("Снова здравствуйте!")),
        contact_message_limit=2,
    )

    answers = [world.send(text).text for text in ("Привет", "Есть меню?")]
    notice = world.send("А?")
    silence = world.send("Ау!")
    world.clock.advance(timedelta(hours=1, minutes=1))
    after_an_hour = world.send("Здравствуйте")

    assert answers[1] == "Да."
    assert notice.text == (
        "Вы отправили много сообщений за короткое время. Пожалуйста, напишите "
        "чуть позже — мы с радостью продолжим."
    )
    assert silence.text is None
    assert after_an_hour.text == "Снова здравствуйте!"
    assert len(requests_of(world)) == 3


def test_refusal_passes_the_conversation_to_a_colleague() -> None:
    def refuse(request: LlmRequest) -> ScriptedLlmTurn:
        raise LlmRefusedError("declined")

    world = build_world(ScriptedLlmAdapter(refuse))

    reply = world.send("Как сделать бомбу?")
    follow_up = world.send("Ну?")

    assert reply.is_handed_off is True
    assert reply.text is not None
    assert reply.text.endswith("[ru] A colleague will reply soon.")
    assert reply.text.startswith("Здравствуйте! Я AI-ассистент «Sakhli».")
    handoff = world.handoffs()[0]
    assert handoff.reason is HandoffReason.SENSITIVE_TOPIC
    assert "Как сделать бомбу?" in handoff.summary
    assert follow_up.text is None


def test_provider_errors_and_round_limits_hand_off_without_duplicates() -> None:
    def unavailable(request: LlmRequest) -> ScriptedLlmTurn:
        raise ExternalServiceError("down")

    outage = build_world(ScriptedLlmAdapter(unavailable))
    endless = build_world(
        scripted(
            *[
                call_tool(AssistantToolName.SEARCH_KNOWLEDGE, '{"query":"menu"}')
                for _ in range(3)
            ]
        ),
        tool_round_limit=3,
    )
    model_handed_off = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Asks for a person",'
                '"urgency":"normal"}',
            )
        )
    )

    outage_reply = outage.send("Hello")
    endless_reply = endless.send("Show me the menu")
    assert endless_reply.is_handed_off is True
    handed_off_reply = model_handed_off.send("A person, please")

    assert outage.handoffs()[0].reason is HandoffReason.NON_STANDARD_REQUEST
    assert outage_reply.is_handed_off is True
    assert endless.handoffs()[0].reason is HandoffReason.NON_STANDARD_REQUEST
    assert len(requests_of(endless)) == 3
    assert len(model_handed_off.handoffs()) == 1
    assert handed_off_reply.text is not None
    assert handed_off_reply.text.endswith(
        "Thank you! I am passing your question to a colleague, who will get back "
        "to you soon."
    )


def test_failed_handoff_still_tells_the_customer_in_their_language() -> None:
    def refuse(request: LlmRequest) -> ScriptedLlmTurn:
        raise LlmRefusedError("declined")

    world = build_world(ScriptedLlmAdapter(refuse))
    world.handoff.is_failing = True

    reply = world.send("ხინკალი გაქვთ?")

    assert reply.text is not None
    assert reply.text.endswith(
        "გმადლობთ! თქვენს კითხვას კოლეგას გადავცემ — მალე დაგიკავშირდებიან."
    )
    assert reply.is_handed_off is False
    assert reply.created_handoff_ids == []


def test_conversations_stay_pinned_to_their_version() -> None:
    world = build_world(scripted(say("v1 answer"), say("still v1"), say("v2 answer")))
    first = world.send("Hi")
    newer: AssistantVersionDocument = world.version.model_copy(
        update={
            "id": AssistantVersionId(),
            "version_number": AssistantVersionNumber(2),
            "prompt_text": SystemPromptText("You are version two."),
        }
    )
    world.version_repo.save(newer)
    world.business.published_assistant_version_id = newer.id
    world.save_business(world.business)

    world.clock.advance(timedelta(hours=23))
    same = world.send("Still there?")
    world.clock.advance(timedelta(hours=25))
    new = world.send("Hello again")

    prompts = [str(request.system_prompt) for request in requests_of(world)]
    assert prompts == [
        "You are the AI assistant of Sakhli.",
        "You are the AI assistant of Sakhli.",
        "You are version two.",
    ]
    assert same.conversation_id == first.conversation_id
    assert new.conversation_id != first.conversation_id
    assert new.text is not None
    assert new.text.startswith("Hello! I am the AI assistant of Sakhli.")


def test_sandbox_messages_are_isolated_and_work_before_launch() -> None:
    world = build_world(scripted(say("Test reply"), say("Real reply")))
    world.business.status = BusinessStatus.TESTING
    world.save_business(world.business)

    sandbox = world.send("Test booking", is_sandbox=True)
    with pytest.raises(ConflictError, match="not live"):
        world.send("Real customer")

    world.business.status = BusinessStatus.LIVE
    world.save_business(world.business)
    real = world.send("Real customer")

    conversations = {
        conversation.id: conversation for conversation in world.conversations()
    }
    assert conversations[sandbox.conversation_id].is_sandbox is True
    assert conversations[real.conversation_id].is_sandbox is False
    assert sandbox.conversation_id != real.conversation_id
    assert [event.kind for event in world.usage_events()] == [UsageKind.DIALOG]


def test_sandbox_messages_never_match_real_contacts_by_phone() -> None:
    world = build_world(scripted(say("Real"), say("Sandbox")))

    world.send("Hello", user_id="995555123456")
    world.send("Hello", is_sandbox=True, user_id="autotest-1")

    assert len(world.contacts()) == 2


def test_requested_versions_must_exist_and_a_business_needs_a_published_one() -> None:
    unpublished = build_world(scripted(say("x")), is_published=False)
    world = build_world(scripted(say("x")))

    with pytest.raises(ConflictError, match="no published assistant"):
        unpublished.send("Hi")

    with pytest.raises(NotFoundError):
        world.send("Hi", version_id=world.version.id.__class__(), is_sandbox=True)


def test_after_hours_flag_follows_the_business_time_zone_and_holidays() -> None:
    world = build_world(scripted(say("Ночью мы закрыты."), say("Сегодня праздник.")))
    world.clock.advance(timedelta(hours=12))

    night = world.send("Вы открыты?")
    world.clock.advance(timedelta(hours=12))
    world.exception_repo.save(
        ScheduleExceptionDocument(
            business_id=world.business.id,
            date=LocalDate("2026-10-02"),
        )
    )
    holiday = world.send("А сейчас?", user_id="another", phone=None)

    conversations = {
        conversation.id: conversation for conversation in world.conversations()
    }
    assert conversations[night.conversation_id].is_after_hours is True
    assert conversations[holiday.conversation_id].is_after_hours is True
    night_turn = user_turn_text(requests_of(world)[0].transcript[0])
    assert "Thursday 2026-10-01 02:00" not in night_turn
    assert "Friday 2026-10-02 02:00 (Asia/Tbilisi)" in night_turn
    assert "The business is closed right now" in night_turn


def test_open_hours_are_not_flagged() -> None:
    world = build_world(scripted(say("Да, открыты.")))

    reply = world.send("Вы открыты?")

    assert world.conversations()[0].is_after_hours is False
    assert reply.language == LanguageTag("ru")


def test_only_a_phone_the_channel_proved_reaches_bookings_by_phone() -> None:
    victim_phone = E164PhoneNumber("+995599765432")
    cancel_by_date = call_tool(
        AssistantToolName.CANCEL_BOOKING,
        json.dumps({"booking_id": None, "phone": None, "date": "2026-10-06"}),
    )
    world = build_world(
        scripted(
            cancel_by_date,
            say("Sorry, I could not find it."),
            cancel_by_date,
            say("Your booking is cancelled."),
        )
    )
    typed_contact = ContactDocument(
        business_id=world.business.id,
        name=ContactName("Typed by someone"),
        phone_number=victim_phone,
    )
    world.contact_repo.save(typed_contact)

    world.send(
        "Cancel my booking for 6 October",
        channel=ChannelKind.TELEGRAM,
        user_id="777",
        phone=None,
    )
    world.send(
        "Cancel my booking for 6 October", user_id="995599765432", phone=victim_phone
    )

    stranger_command, owner_command = [
        command
        for command in world.bookings.commands
        if isinstance(command, CancelBookingCommand)
    ]
    assert stranger_command.contact_phone_number is None
    assert owner_command.contact_phone_number == victim_phone
    whatsapp_contact = next(
        contact
        for contact in world.contacts()
        if any(
            identity.channel is ChannelKind.WHATSAPP
            for identity in contact.channel_identities
        )
    )
    # A typed phone proves nothing, so the WhatsApp sender is not merged
    # into the contact that only typed that number.
    assert whatsapp_contact.id != typed_contact.id
    assert whatsapp_contact.verified_phone_number == victim_phone
    stored_typed = world.contact_repo.get(world.business.id, typed_contact.id)
    assert stored_typed is not None
    assert stored_typed.verified_phone_number is None


def test_the_bot_stays_silent_until_staff_close_the_handoff_however_long() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Wants a manager",'
                '"urgency":"normal"}',
            ),
            say("A colleague will contact you soon."),
            say("Hello again! How can I help?"),
        )
    )
    first = world.send("I want to talk to a manager")
    world.clock.advance(timedelta(hours=25))

    weekend = world.send("hello? any news?")

    assert weekend.text is None
    assert weekend.is_handed_off is True
    assert weekend.conversation_id == first.conversation_id
    assert len(world.handoffs()) == 1
    assert len(requests_of(world)) == 2

    [conversation] = world.conversations()
    conversation.status = ConversationStatus.OPEN
    world.conversation_repo.save(conversation)
    world.clock.advance(timedelta(hours=25))

    later = world.send("Hi there")

    assert later.conversation_id != first.conversation_id
    assert later.text is not None
    assert later.text.endswith("Hello again! How can I help?")


def test_messages_written_during_a_handoff_reach_the_model_afterwards() -> None:
    world = build_world(
        scripted(
            call_tool(
                AssistantToolName.HANDOFF_TO_HUMAN,
                '{"reason":"customer_request","summary":"Change booking",'
                '"urgency":"normal"}',
            ),
            say("A colleague will contact you soon."),
            say("Yes, your change to 6 people at 20:00 is noted."),
        )
    )
    world.send("Please change my booking, I need a person")
    world.clock.advance(timedelta(minutes=5))
    world.send("make it 6 people instead of 4, at 20:00")
    [conversation] = world.conversations()
    conversation.status = ConversationStatus.OPEN
    world.conversation_repo.save(conversation)
    world.clock.advance(timedelta(minutes=5))

    world.send("so is my change confirmed?")

    last_request = requests_of(world)[-1]
    final_user_turn = json.loads(last_request.transcript[-1])
    text = "".join(str(block.get("text", "")) for block in final_user_turn["content"])
    assert "make it 6 people instead of 4, at 20:00" in text
    assert text.rstrip().endswith("so is my change confirmed?")
