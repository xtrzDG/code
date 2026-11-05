"""
The owner's review of aliases is remembered: a suggestion the owner
removed, or a language the model left out, is not asked for again by the
next indexing run (no model call); a new title, or the owner's "Suggest",
asks afresh. A title in none of the business's languages is named in all
of them.
"""

from app.schemas.dto.knowledge_admin import KnowledgeItemPatch
from app.schemas.dto.knowledge_aliases import SuggestKnowledgeAliasesCommand
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.utilities.knowledge.knowledge_item_patches import patch_knowledge_item
from tests.knowledge.cross_language.fakes import PhraseBookAliasSuggester
from tests.knowledge.cross_language.world import CrossLanguageWorld


def owner_patches(
    world: CrossLanguageWorld, item_id: KnowledgeItemId, patch: KnowledgeItemPatch
) -> None:
    template = world.niche_template_registry.get(world.business.niche_key)
    stored = world.knowledge_item_repo.get(world.business.id, item_id)
    assert stored is not None
    world.knowledge_item_repo.save(
        patch_knowledge_item(
            world.business, template, stored, patch, world.wall_clock.now_unix()
        )
    )


def targets(world: CrossLanguageWorld) -> list[list[list[str]]]:
    return [
        [
            [str(language) for language in item.target_languages]
            for item in request.items
        ]
        for request in world.suggester.requests
    ]


def test_a_suggestion_the_owner_removed_is_not_asked_for_again() -> None:
    world = CrossLanguageWorld()
    parking = world.add_item("Do you have parking?")
    world.run_index()
    assert len(world.item(parking).aliases) == 3

    owner_patches(world, parking.id, KnowledgeItemPatch(aliases=[]))
    world.run_index()

    assert len(world.suggester.requests) == 1
    assert world.item(parking).aliases == []


def test_a_language_the_model_left_out_costs_no_further_call() -> None:
    world = CrossLanguageWorld(
        suggester=PhraseBookAliasSuggester(
            {"Do you have parking?": {"ka": "გაქვთ პარკინგი?"}}
        )
    )
    world.add_item("Do you have parking?")

    for _ in range(3):
        world.run_index()

    assert targets(world) == [[["ka", "ru", "he"]]]


def test_a_new_title_or_the_owners_suggest_asks_again() -> None:
    world = CrossLanguageWorld()
    parking = world.add_item("Do you have parking?")
    world.run_index()
    owner_patches(world, parking.id, KnowledgeItemPatch(aliases=[]))

    world.suggest_aliases.run(
        SuggestKnowledgeAliasesCommand(
            user_id=world.owner_id, business_id=world.business.id, item_id=parking.id
        )
    )
    assert len(world.item(parking).aliases) == 3

    owner_patches(
        world,
        parking.id,
        KnowledgeItemPatch(title=KnowledgeTitle("Can I come with children?")),
    )
    world.run_index()

    assert targets(world) == [
        [["ka", "ru", "he"]],
        [["ka", "ru", "he"]],
        [["ka", "ru", "he"]],
    ]


def test_a_title_in_none_of_the_business_languages_is_named_in_all_of_them() -> None:
    world = CrossLanguageWorld(languages=("ru", "ka"))
    world.add_item("Do you have parking?", languages=())
    world.add_item("Есть ли доставка?", languages=())

    world.run_index()

    [request] = world.suggester.requests
    assert [
        (
            str(item.title),
            [str(language) for language in item.source_languages],
            [str(language) for language in item.target_languages],
        )
        for item in request.items
    ] == [
        ("Do you have parking?", ["en"], ["ru", "ka"]),
        ("Есть ли доставка?", ["ru"], ["ka"]),
    ]
