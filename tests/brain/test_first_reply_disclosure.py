"""
Every chat starts by telling the person they talk to an AI assistant, in
their language (EU AI Act Art. 50(1)); in a messenger the first reply also
links the business's privacy notice. The disclosure and the notice exist in
every language the platform reads customers in.
"""

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.utilities.conversations.assistant_texts.ai_disclosure_texts import (
    AI_DISCLOSURE,
)
from app.utilities.conversations.assistant_texts.privacy_notice_texts import (
    PRIVACY_NOTICE_LINE,
)
from app.utilities.conversations.language_evidence.language_evidence_table import (
    LANGUAGE_EVIDENCE,
)
from app.utilities.conversations.language_evidence.script_languages import (
    SHARED_SCRIPT_DEFAULTS,
    SINGLE_LANGUAGE_SCRIPTS,
)
from app.utilities.conversations.language_scoring import evidence_code
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import say, scripted

PRIVACY_URL: str = "https://sakhli.ge/privacy"


def with_privacy_notice(world: BrainWorld) -> None:
    profile = world.profile_repo.get_by_business(world.business.id)
    assert profile is not None
    profile.privacy_notice_url = WebLink(PRIVACY_URL)
    world.profile_repo.save(profile)


def test_the_first_messenger_reply_links_the_privacy_notice_in_italian() -> None:
    world = build_world(scripted(say("Certo, abbiamo un tavolo."), say("Prego!")))
    with_privacy_notice(world)

    first = world.send("Buongiorno, avete un tavolo per due stasera?")
    second = world.send("Grazie mille, a stasera")

    assert first.text is not None
    assert first.text.split("\n") == [
        f"Buongiorno! Sono l'assistente IA di {world.business.name}.",
        f"Informativa sulla privacy: {PRIVACY_URL}",
        "Certo, abbiamo un tavolo.",
    ]
    assert first.disclosure_text == (
        f"Buongiorno! Sono l'assistente IA di {world.business.name}."
    )
    assert second.text == "Prego!"


def test_the_website_chat_shows_the_notice_in_its_footer_instead() -> None:
    world = build_world(scripted(say("Hello!")))
    with_privacy_notice(world)

    reply = world.send("Hi", channel=ChannelKind.WEB_CHAT, phone=None)

    assert reply.text is not None
    assert PRIVACY_URL not in reply.text
    assert reply.text.startswith(
        f"Hello! I am the AI assistant of {world.business.name}."
    )


def test_no_notice_line_without_an_address() -> None:
    world = build_world(scripted(say("Hello!")))

    reply = world.send("Hi")

    assert (
        reply.text == f"Hello! I am the AI assistant of {world.business.name}.\nHello!"
    )


def test_the_disclosure_exists_in_every_language_customers_are_read_in() -> None:
    readable: set[str] = {
        *(evidence_code_of(tag) for tag in LANGUAGE_EVIDENCE),
        *SINGLE_LANGUAGE_SCRIPTS.values(),
        *SHARED_SCRIPT_DEFAULTS.values(),
    }
    disclosed: set[str] = {evidence_code(tag) for tag in AI_DISCLOSURE.values}

    assert readable <= disclosed
    assert {str(tag) for tag in PRIVACY_NOTICE_LINE.values} == {
        str(tag) for tag in AI_DISCLOSURE.values
    }


def evidence_code_of(tag: str) -> str:
    """ "uz-Cyrl" -> "uz": evidence of a language in another script."""

    return tag.split("-")[0]
