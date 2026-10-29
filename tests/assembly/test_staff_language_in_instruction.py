"""Handoff summaries are written for staff, in the staff language."""

from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.testbed import AssemblyTestbed


def assemble(testbed: AssemblyTestbed, owner_language: str) -> tuple[str, str]:
    business = seed_georgian_restaurant(testbed)
    business.owner_language = LanguageTag(owner_language)
    testbed.business_repo.save(business)
    assembled = testbed.assemble(business.id)
    return str(assembled.prompt_text), str(assembled.phone_prompt_text)


def test_chat_and_phone_name_the_staff_language_for_the_summary() -> None:
    chat, phone = assemble(AssemblyTestbed(), "ru")

    rule = (
        "Write the summary in Russian (ru), the language of the business's "
        "staff, even when the customer uses another language."
    )
    assert rule in chat
    assert rule in phone


def test_a_staff_language_customers_do_not_use_is_named_too() -> None:
    chat, _ = assemble(AssemblyTestbed(), "it")

    assert "Write the summary in Italian (it)," in chat
    # Customers are still served in the business languages only.
    assert "The business serves customers in: Georgian (ka), Russian (ru), " in chat
    assert "Italian" not in chat.split("# Style")[0].split("# Languages")[1]
