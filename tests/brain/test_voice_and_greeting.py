import json

import pytest

from app.registries.localization.language_support_data import TEXT_SUPPORTED_LANGUAGES
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.businesses import BusinessStatus, ServiceMode
from app.schemas.constants.channels import ChannelKind, ChannelStatus, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.bookings import CreateBookingCommand
from app.schemas.dto.conversations import CallGreetingRequest, VoiceToolCallRequest
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import (
    LlmToolInputJson,
    ProviderCallId,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
    LanguageTag,
)
from app.utilities.conversations.assistant_texts import (
    AI_DISCLOSURE,
    CALL_GREETING,
    CALL_OPERATOR_HINT,
    CALL_RECORDING_NOTICE,
)
from tests.brain.brain_world import (
    BrainWorld,
    BusinessSetup,
    build_world,
    say,
    scripted,
)

AVAILABILITY_INPUT: str = (
    '{"resource_type":"table","date":"2026-10-02","time":"19:00",'
    '"party_size":2,"duration_minutes":null,"nights":null}'
)
BOOKING_INPUT: str = (
    '{"name":"Levan","phone":null,"resource_type":"table","date":"2026-10-02",'
    '"time":"19:30","party_size":2,"duration_minutes":null,"nights":null,'
    '"notes":null}'
)


def voice_call(
    world: BrainWorld,
    tool_name: AssistantToolName,
    input_json: str,
    *,
    call_id: str = "el_call_1",
    caller: str | None = "+995599123456",
    language: str | None = "ka",
) -> tuple[dict[str, object], bool]:
    result = world.voice_orchestrator.execute(
        VoiceToolCallRequest(
            business_id=world.business.id,
            provider_call_id=ProviderCallId(call_id),
            caller_phone_number=None if caller is None else E164PhoneNumber(caller),
            tool_name=tool_name,
            input_json=LlmToolInputJson(input_json),
            language=None if language is None else LanguageTag(language),
        )
    )
    return json.loads(result.result_json), result.is_error


def test_voice_tool_calls_share_one_call_conversation_and_the_caller() -> None:
    world = build_world(scripted())

    slots, slots_error = voice_call(
        world, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT
    )
    booking, booking_error = voice_call(
        world, AssistantToolName.CREATE_BOOKING, BOOKING_INPUT
    )

    assert (slots_error, booking_error) == (False, False)
    assert slots["slots"] == [
        {
            "resource_id": slots["slots"][0]["resource_id"],  # type: ignore[index]
            "resource_name": "Table by the window",
            "unit": "time_slot",
            "date": "2026-10-02",
            "time": "19:30",
        },
        {
            "resource_id": slots["slots"][1]["resource_id"],  # type: ignore[index]
            "resource_name": "Table by the window",
            "unit": "time_slot",
            "date": "2026-10-02",
            "time": "20:00",
        },
    ]
    conversations = world.conversations()
    assert len(conversations) == 1
    conversation = conversations[0]
    assert conversation.channel is ChannelKind.PHONE
    assert conversation.channel_user_id == "el_call_1"
    assert conversation.assistant_version_id == world.version.id
    assert conversation.language == "ka"
    contact = world.contacts()[0]
    assert contact.phone_number == "+995599123456"
    command = world.bookings.commands[0]
    assert isinstance(command, CreateBookingCommand)
    assert command.contact_id == contact.id
    assert command.contact_phone_number == "+995599123456"
    assert command.source_channel is ChannelKind.PHONE
    assert booking["time"] == "19:30"
    feed = world.messages(conversation.id)
    assert [message.author for message in feed] == [MessageAuthor.SYSTEM] * 2
    assert all(message.direction is MessageDirection.OUTBOUND for message in feed)
    assert [message.tool_calls[0].tool_name for message in feed] == [
        AssistantToolName.CHECK_AVAILABILITY,
        AssistantToolName.CREATE_BOOKING,
    ]


def test_a_second_call_of_the_same_caller_is_another_conversation() -> None:
    world = build_world(scripted())

    voice_call(world, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT)
    voice_call(
        world,
        AssistantToolName.CHECK_AVAILABILITY,
        AVAILABILITY_INPUT,
        call_id="el_call_2",
        language=None,
    )

    assert len(world.conversations()) == 2
    assert len(world.contacts()) == 1
    assert {conversation.language for conversation in world.conversations()} == {"ka"}


def test_withheld_numbers_and_bad_input_are_handled() -> None:
    world = build_world(scripted())

    result, is_error = voice_call(
        world,
        AssistantToolName.CREATE_BOOKING,
        '{"name":"Anon","date":"soon","party_size":2}',
        caller=None,
    )

    assert is_error is True
    assert "date" in str(result["error"])
    assert world.contacts()[0].phone_number is None
    assert world.contacts()[0].channel_identities[0].channel_user_id == "el_call_1"


def test_voice_tools_follow_leads_only_mode() -> None:
    world = build_world(scripted())
    world.business.service_mode = ServiceMode.LEADS_ONLY
    world.save_business(world.business)

    result, is_error = voice_call(
        world, AssistantToolName.CREATE_BOOKING, BOOKING_INPUT
    )

    assert is_error is True
    assert "not available" in str(result["error"])


def test_voice_tool_calls_need_a_known_business_with_a_published_version() -> None:
    unpublished = build_world(scripted(), is_published=False)
    world = build_world(scripted())

    with pytest.raises(ConflictError):
        voice_call(
            unpublished, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT
        )

    world.business = world.business.model_copy(update={"id": BusinessId()})
    with pytest.raises(NotFoundError):
        voice_call(world, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT)


def test_a_paused_business_takes_no_new_calls_but_a_call_in_progress_goes_on() -> None:
    world = build_world(scripted())
    first, _ = voice_call(
        world, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT
    )
    world.business.status = BusinessStatus.PAUSED
    world.save_business(world.business)

    ongoing, ongoing_error = voice_call(
        world, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT
    )
    with pytest.raises(ConflictError, match="not live"):
        voice_call(
            world,
            AssistantToolName.CHECK_AVAILABILITY,
            AVAILABILITY_INPUT,
            call_id="el_call_2",
        )

    assert ongoing_error is False
    assert ongoing == first
    assert len(world.conversations()) == 1


def test_a_new_call_needs_voice_in_the_plan_and_a_connected_number() -> None:
    downgraded = build_world(scripted())
    downgraded.business.plan_key = PlanKey.CHAT
    downgraded.save_business(downgraded.business)
    disconnected = build_world(scripted())
    for channel in disconnected.channel_repo.list_by_business(disconnected.business.id):
        channel.status = ChannelStatus.DISABLED
        disconnected.channel_repo.save(channel)

    with pytest.raises(ConflictError, match="plan"):
        voice_call(downgraded, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT)

    with pytest.raises(ConflictError, match="phone number"):
        voice_call(
            disconnected, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT
        )


def test_phone_conversation_from_voice_calls_continues_in_chat_turns() -> None:
    world = build_world(scripted(say("კი, ხვალ 19:30-ზე გელოდებით.")))
    voice_call(world, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT)

    reply = world.send(
        "ხვალ მაგიდა მინდა",
        channel=ChannelKind.PHONE,
        user_id="el_call_1",
        phone=E164PhoneNumber("+995599123456"),
    )

    assert reply.conversation_id == world.conversations()[0].id
    assert reply.text == "კი, ხვალ 19:30-ზე გელოდებით."


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (
            None,
            "გამარჯობა! ეს არის Sakhli-ის AI-ასისტენტი. საუბარი იწერება. "
            "თანამშრომელთან სასაუბროდ თქვით „ოპერატორი“.",
        ),
        (
            "ru",
            "Здравствуйте! Это AI-ассистент «Sakhli». Разговор записывается. "
            "Чтобы поговорить с сотрудником, скажите «оператор».",
        ),
        (
            "en",
            "Hello! This is the AI assistant of Sakhli. The call is recorded. "
            'To talk to a staff member, say "operator".',
        ),
        (
            "he",
            "שלום! כאן עוזר ה-AI של Sakhli. השיחה מוקלטת. "
            'כדי לדבר עם נציג, אמרו "נציג".',
        ),
        (
            "ar",
            "مرحبًا! معك مساعد الذكاء الاصطناعي لدى Sakhli. يتم تسجيل المكالمة. "
            'للتحدث مع أحد الموظفين، قل "موظف".',
        ),
        (
            "sw",
            "Habari! Huyu ni msaidizi wa AI wa Sakhli. Simu hii inarekodiwa. "
            "Ili kuzungumza na mfanyakazi, sema “opereta”.",
        ),
        (
            "ko",
            "안녕하세요! Sakhli의 AI 어시스턴트입니다. 이 통화는 녹음됩니다. "
            "직원과 통화하시려면 “상담원”이라고 말씀해 주세요.",
        ),
    ],
)
def test_call_greeting_discloses_the_ai_recording_and_the_operator(
    language: str | None,
    expected: str,
) -> None:
    world = build_world(scripted())

    greeting = world.greeting.run(
        CallGreetingRequest(
            business_id=world.business.id,
            language=None if language is None else LanguageTag(language),
        )
    )

    assert greeting.text == expected
    assert greeting.language == (language or "ka")


def test_a_language_without_a_greeting_is_greeted_and_labelled_in_english() -> None:
    world = build_world(scripted())

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("yo"))
    )

    assert greeting.text.startswith("Hello! This is the AI assistant of Sakhli.")
    assert greeting.language == "en"


@pytest.mark.parametrize("country", ["GE", "DE", "US", "ZZ"])
def test_recorded_calls_always_say_so_whatever_the_profile_says(
    country: str,
) -> None:
    world = build_world(
        scripted(),
        BusinessSetup(country_code=country if country != "ZZ" else "GE"),
    )
    profile = world.profile_repo.get_by_business(world.business.id)
    assert isinstance(profile, BusinessProfileDocument)
    profile.is_recording_notice_enabled = False
    world.profile_repo.save(profile)
    if country == "ZZ":
        world.business.country_code = CountryCode("ZZ")
        world.save_business(world.business)

    greeting = world.greeting.run(
        CallGreetingRequest(business_id=world.business.id, language=LanguageTag("en"))
    )

    assert "The call is recorded." in greeting.text


def test_greeting_of_an_unknown_business_is_not_found() -> None:
    world = build_world(scripted())

    with pytest.raises(NotFoundError):
        world.greeting.run(CallGreetingRequest(business_id=BusinessId()))


@pytest.mark.parametrize(
    "text",
    [AI_DISCLOSURE, CALL_GREETING, CALL_RECORDING_NOTICE, CALL_OPERATOR_HINT],
)
def test_customer_facing_openers_exist_in_every_supported_text_language(
    text: LocalizedText,
) -> None:
    missing = sorted(
        str(tag) for tag in TEXT_SUPPORTED_LANGUAGES if tag not in text.values
    )

    assert missing == []
