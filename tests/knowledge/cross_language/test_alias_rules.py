"""How aliases are checked, kept through edits and planned for the model."""

import pytest

from app.schemas.constants.knowledge import KnowledgeAliasStatus, KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeAlias
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.use_cases.knowledge.aliases.alias_rounds import plan_alias_items
from app.utilities.knowledge.aliases.alias_rules import carry_aliases, check_aliases
from tests.knowledge.cross_language.world import CrossLanguageWorld

APPROVED = KnowledgeAliasStatus.APPROVED
SUGGESTED = KnowledgeAliasStatus.SUGGESTED
LANGUAGES = [LanguageTag("en"), LanguageTag("ka"), LanguageTag("ru")]


def alias(language: str, text: str, status: KnowledgeAliasStatus) -> KnowledgeAlias:
    return KnowledgeAlias(
        language=LanguageTag(language), text=KnowledgeAliasText(text), status=status
    )


def test_aliases_are_kept_once_per_language_approved_first() -> None:
    checked = check_aliases(
        [
            alias("ka", "გაქვთ  პარკინგი?", SUGGESTED),
            alias("ka", "გაქვთ პარკინგი", APPROVED),
            alias("ru", "Есть ли парковка?", SUGGESTED),
        ],
        LANGUAGES,
    )

    assert [(str(a.language), str(a.text), a.status) for a in checked] == [
        ("ka", "გაქვთ პარკინგი", APPROVED),
        ("ru", "Есть ли парковка?", SUGGESTED),
    ]


@pytest.mark.parametrize("text", ["  Parking", "Parking ", "Park\ning", "\tParking"])
def test_an_alias_text_with_surrounding_spaces_or_control_characters_is_refused(
    text: str,
) -> None:
    with pytest.raises(ValueError):
        KnowledgeAliasText(text)


def test_an_alias_in_another_language_or_a_fourth_one_is_refused() -> None:
    with pytest.raises(ValidationFailedError, match="not a language"):
        check_aliases([alias("he", "יש חניה?", APPROVED)], LANGUAGES)

    with pytest.raises(ValidationFailedError, match="At most 3"):
        check_aliases(
            [alias("ru", f"Парковка {number}", APPROVED) for number in range(4)],
            LANGUAGES,
        )


def test_a_new_title_keeps_the_owners_aliases_and_drops_the_models() -> None:
    world = CrossLanguageWorld()
    item = world.add_item(
        "Do you have parking?",
        aliases=[
            ("ka", "გაქვთ პარკინგი?", APPROVED),
            ("ru", "Есть ли парковка?", SUGGESTED),
        ],
    )

    same_title = carry_aliases(item, KnowledgeTitle("do you have  PARKING"))
    new_title = carry_aliases(item, KnowledgeTitle("Where can I leave my car?"))

    assert [str(a.language) for a in same_title] == ["ka", "ru"]
    assert [str(a.language) for a in new_title] == ["ka"]


def test_items_written_or_named_in_every_language_need_no_model() -> None:
    world = CrossLanguageWorld(languages=("en", "ka", "ru"))
    world.add_item("Do you have parking?", languages=("en", "ka", "ru"))
    world.add_item(
        "Can I come with children?",
        aliases=[
            ("ka", "ბავშვებთან ერთად?", SUGGESTED),
            ("ru", "С детьми можно?", APPROVED),
        ],
    )
    draft = world.add_item("When is the live music?")
    world.knowledge_item_repo.save(
        draft.model_copy(update={"import_batch_id": MenuImportBatchId()})
    )
    russian = world.add_item(
        "Есть ли доставка?", kind=KnowledgeItemKind.FAQ, languages=()
    )

    planned = plan_alias_items(
        world.knowledge_item_repo.list_by_business(world.business.id),
        world.business,
        world.language_detector,
    )

    # The unconfirmed draft waits; the Russian question without languages is
    # detected as Russian and named in English and Georgian.
    assert [
        (item.item_id, [str(t) for t in item.target_languages]) for item in planned
    ] == [(russian.id, ["en", "ka"])]
    assert [str(language) for language in planned[0].source_languages] == ["ru"]
