"""
The owner edits an item while the index job waits for the alias model:
the edit is kept, the job adds suggestions only where the item still has
no alias, and suggestions for a title that changed meanwhile are dropped.
The interleaving is forced with events, not timing.
"""

import threading

from app.schemas.constants.knowledge import KnowledgeAliasStatus
from app.schemas.domain.knowledge import KnowledgeAlias
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemPatch,
    UpdateKnowledgeItemCommand,
)
from app.schemas.dto.knowledge_aliases import AliasSuggestionRequest
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.knowledge.update_knowledge_item_use_case import (
    UpdateKnowledgeItemUseCase,
)
from tests.knowledge.cross_language.fakes import PhraseBookAliasSuggester
from tests.knowledge.cross_language.world import CrossLanguageWorld

WAIT_SECONDS: float = 10.0


class PausedModel:
    """Holds the model's answer until the test has made its edit."""

    def __init__(self) -> None:
        self.asked: threading.Event = threading.Event()
        self.may_answer: threading.Event = threading.Event()

    def __call__(self, request: AliasSuggestionRequest) -> None:
        del request
        self.asked.set()
        assert self.may_answer.wait(WAIT_SECONDS)


def paused_world() -> tuple[CrossLanguageWorld, PausedModel]:
    paused = PausedModel()
    return (
        CrossLanguageWorld(suggester=PhraseBookAliasSuggester(before_answer=paused)),
        paused,
    )


def edit_during_the_call(
    world: CrossLanguageWorld, paused: PausedModel, patch: KnowledgeItemPatch
) -> None:
    job = threading.Thread(target=world.run_index)
    job.start()
    assert paused.asked.wait(WAIT_SECONDS)
    update = UpdateKnowledgeItemUseCase(
        business_repo=world.business_repo,
        knowledge_item_repo=world.knowledge_item_repo,
        resource_repo=world.resource_repo,
        niche_template_registry=world.niche_template_registry,
        wall_clock=world.wall_clock,
    )
    [item] = world.knowledge_item_repo.list_by_business(world.business.id)
    update.run(
        UpdateKnowledgeItemCommand(
            business_id=world.business.id, item_id=item.id, patch=patch
        )
    )
    paused.may_answer.set()
    job.join(WAIT_SECONDS)
    assert not job.is_alive()


def test_an_owner_edit_made_during_the_model_call_is_kept() -> None:
    world, paused = paused_world()
    parking = world.add_item("Do you have parking?")
    owner_alias = KnowledgeAlias(
        language=LanguageTag("ka"),
        text=KnowledgeAliasText("პარკინგი გაქვთ?"),
        status=KnowledgeAliasStatus.APPROVED,
    )

    edit_during_the_call(
        world,
        paused,
        KnowledgeItemPatch(
            body=KnowledgeBody("Free parking for guests."), aliases=[owner_alias]
        ),
    )

    stored = world.item(parking)
    assert str(stored.body) == "Free parking for guests."
    assert {str(alias.language): str(alias.text) for alias in stored.aliases} == {
        "ka": "პარკინგი გაქვთ?",
        "ru": "Есть ли парковка?",
        "he": "יש חניה?",
    }
    assert [alias.status for alias in stored.aliases] == [
        KnowledgeAliasStatus.APPROVED,
        KnowledgeAliasStatus.SUGGESTED,
        KnowledgeAliasStatus.SUGGESTED,
    ]


def test_suggestions_for_a_title_changed_during_the_call_are_dropped() -> None:
    world, paused = paused_world()
    parking = world.add_item("Do you have parking?")

    edit_during_the_call(
        world,
        paused,
        KnowledgeItemPatch(title=KnowledgeTitle("Where can I leave my car?")),
    )

    stored = world.item(parking)
    assert str(stored.title) == "Where can I leave my car?"
    assert stored.aliases == []
