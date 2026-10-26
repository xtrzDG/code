"""
What new owners read once a version is published: the catalog's niche
list, a niche's questions and its starter answers carry the version's
texts; niches without a version read exactly as the code writes them.
"""

from app.schemas.constants.niches import NicheKey
from app.schemas.typings.localization.constrained_strings import CountryCode
from tests.niche_texts.niche_text_world import EN, RESTAURANT, RU, NicheTextWorld

GE = CountryCode("GE")
IL = CountryCode("IL")


def test_the_niche_list_carries_the_published_names_only() -> None:
    world = NicheTextWorld()
    world.save(RU, name="Рестораны, кафе и бары")
    world.publish()

    templates = world.effective_templates.list_all()

    assert [template.key for template in templates] == list(NicheKey)
    assert str(templates[0].names.values[RU]) == "Рестораны, кафе и бары"
    assert (
        templates[0].names.values[EN]
        == world.code_templates.get(RESTAURANT).names.values[EN]
    )
    assert templates[1:] == world.code_templates.list_all()[1:]


def test_starter_answers_carry_the_published_texts_over_the_countrys_week() -> None:
    world = NicheTextWorld()
    world.save(
        RU,
        starters__tone="Тепло, по-домашнему, коротко",
        starters__faq__parking__question="Где оставить машину?",
    )
    world.publish()

    starters = world.effective_starters.get(RESTAURANT, IL)
    code = world.code_starters.get(RESTAURANT, IL)

    assert str(starters.tones.values[RU]) == "Тепло, по-домашнему, коротко"
    parking = next(faq for faq in starters.faq if str(faq.key) == "parking")
    assert str(parking.questions.values[RU]) == "Где оставить машину?"
    assert starters.hours == code.hours
    assert world.effective_starters.get(NicheKey.HOTEL, GE) == world.code_starters.get(
        NicheKey.HOTEL, GE
    )


def test_a_reset_brings_the_code_wording_back_for_new_owners() -> None:
    world = NicheTextWorld()
    world.save(RU, starters__tone="Тепло и коротко")
    world.publish()
    world.revert(0)

    assert world.effective_starters.get(RESTAURANT, GE) == world.code_starters.get(
        RESTAURANT, GE
    )
    assert world.effective_templates.get(RESTAURANT) == world.code_templates.get(
        RESTAURANT
    )
