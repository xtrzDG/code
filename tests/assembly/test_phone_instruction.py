"""The phone instruction: spoken facts, no links, the disclosure in the greeting."""

from app.schemas.constants.billing import PlanKey
from app.transformers.assembly.phone_instruction_transformer import (
    PhoneInstructionTransformer,
)
from app.utilities.assembly.assistant_tools import select_assistant_tools
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.test_assistant_instruction import build_instruction_source
from tests.assembly.testbed import AssemblyTestbed

PHONE_SECTION_TITLES: list[str] = [
    "# Role",
    "# Languages",
    "# Style",
    "# Facts",
    "# Bookings",
    "# Handing off to a human",
    "# Never",
    "# Rules for this type of business",
    "# Emergencies",
    "# Answer format",
    "# Example exchanges",
]


def assemble_phone_prompt(testbed: AssemblyTestbed) -> str:
    version = testbed.assemble(seed_georgian_restaurant(testbed).id)
    assert version.phone_prompt_text is not None
    return str(version.phone_prompt_text)


def test_a_voice_version_gets_its_own_phone_instruction() -> None:
    testbed = AssemblyTestbed()
    version = testbed.assemble(seed_georgian_restaurant(testbed).id)

    assert version.phone_prompt_text is not None
    assert version.phone_prompt_text != version.prompt_text
    positions = [
        str(version.phone_prompt_text).index(title + "\n")
        for title in PHONE_SECTION_TITLES
    ]
    assert positions == sorted(positions)


def test_a_chat_version_has_no_phone_instruction() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed, plan_key=PlanKey.CHAT)

    version = testbed.assemble(business.id)

    assert version.phone_prompt_text is None


def test_the_greeting_carries_the_disclosure_on_the_phone() -> None:
    prompt = assemble_phone_prompt(AssemblyTestbed())

    assert "You answer the customers of this business on the phone" in prompt
    assert "The greeting of every call already says that you are the AI" in prompt
    assert "say honestly that you are an AI assistant" in prompt
    assert "first reply of every conversation" not in prompt


def test_facts_are_written_the_way_they_are_said() -> None:
    prompt = assemble_phone_prompt(AssemblyTestbed())

    assert "Price: 18 Georgian laris" in prompt
    assert "- Deposit: 50 Georgian laris" in prompt
    assert "GEL" not in prompt
    assert "- Opening hours on Friday: from 12:00 to 15:00, from 18:00 to midnight" in (
        prompt
    )
    assert "- Special day 31 December 2026: Open from 12:00 to 18:00" in prompt
    assert "2026-12-31" not in prompt


def test_links_are_never_in_the_phone_instruction() -> None:
    prompt = assemble_phone_prompt(AssemblyTestbed())

    assert "https://" not in prompt
    assert (
        "- Links the caller can get as a text message with send_link: Location on "
        "the map, Menu link, Online booking page"
    ) in prompt
    assert "Never read a link or a web address aloud." in prompt
    assert 'say "I will text you the link"' in prompt
    assert "never promise a message" in prompt


def test_without_send_link_links_are_simply_left_out() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    version = testbed.assemble(business.id)
    source = build_instruction_source(
        testbed,
        business,
        select_assistant_tools(takes_bookings=True, has_links=False),
    ).model_copy(update={"facts": testbed.version(business.id, version.id).facts})

    prompt = str(PhoneInstructionTransformer().transform(source))

    assert "https://" not in prompt
    assert "send_link" not in prompt
    assert "Never read a link or a web address aloud." in prompt


def test_the_phone_keeps_every_shared_rule() -> None:
    testbed = AssemblyTestbed()
    version = testbed.assemble(seed_georgian_restaurant(testbed).id)
    chat_prompt = str(version.prompt_text)
    phone_prompt = str(version.phone_prompt_text)

    for title in ("# Bookings", "# Handing off to a human", "# Never", "# Emergencies"):
        chat_section = chat_prompt.split(title + "\n")[1].split("\n\n")[0]
        assert title + "\n" + chat_section in phone_prompt


def test_the_phone_answers_in_short_spoken_sentences() -> None:
    prompt = assemble_phone_prompt(AssemblyTestbed())
    answer_format = prompt.split("# Answer format\n")[1].split("\n\n")[0]

    assert "You are speaking on the phone" in answer_format
    assert "never say a currency code" in answer_format
    assert "digit by digit" in answer_format
    assert "markdown" in answer_format
