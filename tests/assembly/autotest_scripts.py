"""Scripted autotest behaviour: scenario keys, customer and assistant texts, replies."""

import re
from collections.abc import Callable

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.dto.conversations import AssistantReply, InboundMessage, LlmRequest
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag

CHANNEL_USER_PATTERN: re.Pattern[str] = re.compile(
    r"^autotest-autotest_run_[0-9a-f\-]{36}-(?P<key>[a-z0-9_\-]+)$"
)
LANGUAGE_TAG_PATTERN: re.Pattern[str] = re.compile(r"language tag ([A-Za-z\-]+)\)")
SCENARIO_LINE_PATTERN: re.Pattern[str] = re.compile(r"^Scenario: (\S+) ", re.MULTILINE)
DONE: str = "[DONE]"
CUSTOMER_TEXTS: dict[str, str] = {
    "ka": "გამარჯობა, მინდა მაგიდის დაჯავშნა ხვალ",
    "ru": "Здравствуйте, хочу забронировать стол на завтра",
    "en": "Hello, I would like to book a table for tomorrow",
    "it": "Buongiorno, vorrei prenotare un tavolo per domani",
    "ja": "こんにちは、明日の予約をお願いします",
    "he": "שלום, אני רוצה לקבוע תור למחר",
    "ar": "مرحبا، أريد حجز موعد غدا",
}
ASSISTANT_TEXTS: dict[str, str] = {
    "ka": "გამარჯობა! მე ვარ AI ასისტენტი. როგორ დაგეხმაროთ?",
    "ru": "Здравствуйте! Я AI-ассистент. Чем могу помочь?",
    "en": "Hello! I am the AI assistant. How can I help?",
    "it": "Buongiorno! Sono l'assistente AI. Come posso aiutarla?",
    "ja": "こんにちは！AIアシスタントです。ご用件をどうぞ。",
    "he": "שלום! אני עוזר בינה מלאכותית. איך אפשר לעזור?",
    "ar": "مرحبا! أنا المساعد الذكي. كيف يمكنني مساعدتك؟",
}
PERFECT_SCORES: dict[str, int] = {
    "facts_and_prices": 5,
    "booking_data": 5,
    "ai_disclosure": 5,
    "handoff": 5,
    "language": 5,
}

type CustomerScript = Callable[[LlmRequest, int], str]
type ReplyScript = Callable[[InboundMessage, str, int], AssistantReply]


def read_scenario_key(message: InboundMessage) -> str:
    """Scenario key encoded in the autotest channel user id."""

    match: re.Match[str] | None = CHANNEL_USER_PATTERN.match(
        str(message.channel_user_id)
    )
    assert match is not None, message.channel_user_id
    return match.group("key")


def read_scenario_language(scenario_key: str) -> str:
    return scenario_key.split("__")[1]


def read_scenario_kind(scenario_key: str) -> AutotestScenarioKind:
    return AutotestScenarioKind(scenario_key.split("__")[0])


def default_customer_script(request: LlmRequest, turn_index: int) -> str:
    """One message in the scenario language, then [DONE]."""

    if turn_index >= 1:
        return DONE

    match: re.Match[str] | None = LANGUAGE_TAG_PATTERN.search(
        str(request.system_prompt)
    )
    assert match is not None
    return CUSTOMER_TEXTS[match.group(1)]


def default_reply_script(
    message: InboundMessage,
    scenario_key: str,
    turn_index: int,
) -> AssistantReply:
    """
    Replies in the scenario language; books in BOOKING scenarios and hands
    off in HUMAN_REQUEST and EMERGENCY scenarios.
    """

    del turn_index
    language: str = read_scenario_language(scenario_key)
    kind: AutotestScenarioKind = read_scenario_kind(scenario_key)
    is_handed_off: bool = kind in (
        AutotestScenarioKind.HUMAN_REQUEST,
        AutotestScenarioKind.EMERGENCY,
    )
    del message
    return build_reply(
        language,
        is_handed_off=is_handed_off,
        is_booked=kind is AutotestScenarioKind.BOOKING,
    )


def build_reply(
    language: str,
    *,
    text: str | None = None,
    is_handed_off: bool = False,
    is_booked: bool = False,
    is_lead_created: bool = False,
) -> AssistantReply:
    """An assistant reply in a scenario language (key spelling, e.g. "ka")."""

    return AssistantReply(
        conversation_id=ConversationId(),
        text=MessageText(text if text is not None else ASSISTANT_TEXTS[language]),
        language=LanguageTag(language),
        is_handed_off=is_handed_off,
        created_booking_ids=[BookingId()] if is_booked else [],
        created_lead_ids=[LeadId()] if is_lead_created else [],
        created_handoff_ids=[HandoffId()] if is_handed_off else [],
    )
