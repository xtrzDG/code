"""
"Suggest translations" for one item in the editor: one call names it in the
languages it still lacks, a second costs nothing, and the calls are limited.
"""

import pytest

from app.schemas.constants.knowledge import KnowledgeAliasStatus
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails
from app.schemas.dto.knowledge_aliases import SuggestKnowledgeAliasesCommand
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    RateLimitedError,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from tests.knowledge.cross_language.world import CrossLanguageWorld


def suggest(
    world: CrossLanguageWorld, item_id: KnowledgeItemId
) -> KnowledgeItemDetails:
    return world.suggest_aliases.run(
        SuggestKnowledgeAliasesCommand(
            user_id=world.owner_id, business_id=world.business.id, item_id=item_id
        )
    )


def test_the_owner_gets_suggestions_for_the_missing_languages_once() -> None:
    world = CrossLanguageWorld()
    item = world.add_item(
        "Do you have parking?",
        aliases=[("ka", "პარკინგი?", KnowledgeAliasStatus.APPROVED)],
        is_active=False,
    )

    details = suggest(world, item.id)
    again = suggest(world, item.id)

    assert [
        (str(alias.language), str(alias.text), alias.status)
        for alias in details.aliases
    ] == [
        ("ka", "პარკინგი?", KnowledgeAliasStatus.APPROVED),
        ("ru", "Есть ли парковка?", KnowledgeAliasStatus.SUGGESTED),
        ("he", "יש חניה?", KnowledgeAliasStatus.SUGGESTED),
    ]
    assert [
        [str(language) for language in request.items[0].target_languages]
        for request in world.suggester.requests
    ] == [["ru", "he"]]
    assert again.aliases == details.aliases


def test_an_item_of_another_business_is_missing() -> None:
    world = CrossLanguageWorld()

    with pytest.raises(NotFoundError):
        suggest(world, KnowledgeItemId())


def test_suggestions_are_limited_to_sixty_calls_an_hour_per_business() -> None:
    world = CrossLanguageWorld(languages=("en", "ka"))
    items = [world.add_item(f"Question {number}?") for number in range(61)]

    for item in items[:60]:
        suggest(world, item.id)

    with pytest.raises(RateLimitedError):
        suggest(world, items[60].id)
    assert len(world.suggester.requests) == 60
