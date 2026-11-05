"""
The engine answers in the customer's language, also one the business did
not list: the disclosure, the platform's notices and the model's context
line follow it, and a short "ok" keeps the conversation's language.
"""

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import LlmRefusedError
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of, user_turn_text
from tests.brain.scripted_turns import say, scripted


def test_a_hebrew_writer_gets_the_hebrew_disclosure_in_a_georgian_business() -> None:
    world = build_world(scripted(say("בטח, יש מקום.")))

    reply = world.send("שלום, יש לכם מקום לשניים מחר?")

    assert world.business.languages == ["ka", "ru", "en"]
    assert reply.language == "he"
    assert reply.text == "שלום! אני עוזר ה-AI של Sakhli.\nבטח, יש מקום."
    assert [message.language for message in world.messages(reply.conversation_id)] == [
        "he",
        "he",
    ]
    assert world.conversations()[0].language == "he"
    assert world.contacts()[0].language == "he"
    context = user_turn_text(requests_of(world)[0].transcript[0])
    assert "Reply language: Hebrew (he)." in context


def test_a_german_writer_gets_the_german_disclosure() -> None:
    world = build_world(scripted(say("Ja, gern.")))

    reply = world.send("Hallo, haben Sie heute Abend einen Tisch frei?")

    assert reply.language == "de"
    assert reply.text == "Hallo! Ich bin der KI-Assistent von Sakhli.\nJa, gern."


def test_georgian_in_latin_letters_is_answered_in_georgian() -> None:
    world = build_world(scripted(say("დიახ, ხვალ 20:00-ზე თავისუფალია.")))

    reply = world.send("gamarjoba, xval magida mchirdeba 4 kacze")

    assert reply.language == "ka"
    assert reply.text is not None
    assert reply.text.startswith("გამარჯობა! მე ვარ Sakhli-ის AI-ასისტენტი.")
    context = user_turn_text(requests_of(world)[0].transcript[0])
    assert (
        "Reply language: Georgian (ka). The customer types it in Latin letters; "
        "reply in Georgian script unless they ask for Latin letters."
    ) in context


def test_ok_keeps_a_russian_conversation_in_russian() -> None:
    world = build_world(scripted(say("Да, есть."), say("Ждём вас!")))

    world.send("Здравствуйте, можно столик на завтра?")
    reply = world.send("ok")

    assert reply.language == "ru"
    assert world.conversations()[0].language == "ru"
    second_context = user_turn_text(requests_of(world)[1].transcript[-1])
    assert "Reply language: Russian (ru)." in second_context


def test_the_colleague_notice_is_in_the_customer_language() -> None:
    def refuse(request: LlmRequest) -> ScriptedLlmTurn:
        raise LlmRefusedError("declined")

    world = build_world(ScriptedLlmAdapter(refuse))
    world.handoff.is_failing = True

    reply = world.send("שלום, אפשר לדבר עם מישהו?")

    assert reply.text is not None
    assert reply.text.endswith("תודה! אני מעביר את השאלה שלך לעמית, שיחזור אליך בקרוב.")


def test_the_limit_notice_is_in_the_customer_language() -> None:
    world = build_world(
        scripted(say("שלום!"), say("כן.")),
        contact_message_limit=2,
    )

    for text in ("שלום, יש מקום מחר?", "ולשלושה אנשים?"):
        world.send(text)

    notice = world.send("👍")

    assert notice.language == "he"
    assert notice.text == (
        "שלחת הרבה הודעות בזמן קצר. אנא כתוב שוב מעט מאוחר יותר, ונשמח להמשיך."
    )


def test_the_contact_language_follows_what_the_customer_writes() -> None:
    world = build_world(scripted(say("בטח."), say("Sure."), say("Sure!")))

    world.send("שלום, יש מקום?")
    world.send("👍")
    assert world.contacts()[0].language == "he"

    world.send("Sorry, can we switch to English please?")
    assert world.contacts()[0].language == "en"
