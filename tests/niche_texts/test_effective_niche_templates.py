"""
What new owners read once a version is published: the catalog's niche
list, a niche's questions and its starter answers carry the version's
texts; niches without a version read exactly as the code writes them.
"""

from app.schemas.constants.niches import NicheKey
from app.schemas.typings.localization.constrained_strings import CountryCode
from tests.niche_texts.niche_text_world import EN, IT, RESTAURANT, NicheTextWorld

GE = CountryCode("GE")
IL = CountryCode("IL")


def test_the_niche_list_carries_the_published_names_only() -> None:
    world = NicheTextWorld()
    world.save(IT, name="Ristoranti, caffè e bar")
    world.publish()

    templates = world.effective_templates.list_all()

    assert [template.key for template in templates] == list(NicheKey)
    assert str(templates[0].names.values[IT]) == "Ristoranti, caffè e bar"
    assert (
        templates[0].names.values[EN]
        == world.code_templates.get(RESTAURANT).names.values[EN]
    )
    assert templates[1:] == world.code_templates.list_all()[1:]


def test_starter_answers_carry_the_published_texts_over_the_countrys_week() -> None:
    world = NicheTextWorld()
    world.save(
        IT,
        starters__tone="Caldo, familiare, breve",
        starters__faq__parking__question="Dove si lascia la macchina?",
    )
    world.publish()

    starters = world.effective_starters.get(RESTAURANT, IL)
    code = world.code_starters.get(RESTAURANT, IL)

    assert str(starters.tones.values[IT]) == "Caldo, familiare, breve"
    parking = next(faq for faq in starters.faq if str(faq.key) == "parking")
    assert str(parking.questions.values[IT]) == "Dove si lascia la macchina?"
    assert starters.hours == code.hours
    assert world.effective_starters.get(NicheKey.HOTEL, GE) == world.code_starters.get(
        NicheKey.HOTEL, GE
    )


def test_a_reset_brings_the_code_wording_back_for_new_owners() -> None:
    world = NicheTextWorld()
    world.save(IT, starters__tone="Caldo e breve")
    world.publish()
    world.revert(0)

    assert world.effective_starters.get(RESTAURANT, GE) == world.code_starters.get(
        RESTAURANT, GE
    )
    assert world.effective_templates.get(RESTAURANT) == world.code_templates.get(
        RESTAURANT
    )
