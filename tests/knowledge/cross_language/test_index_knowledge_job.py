"""
The index_knowledge job: one model call names the items in the business's
other languages, its cost is recorded, vectors are kept current, and an
unchanged knowledge base costs nothing.
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.knowledge import KnowledgeAliasStatus, KnowledgeItemKind
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.knowledge.strings import KnowledgeBody
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from tests.knowledge.cross_language.world import CrossLanguageWorld

SUGGESTED = KnowledgeAliasStatus.SUGGESTED


def aliases_of(world: CrossLanguageWorld, title: str) -> dict[str, str]:
    item = next(
        item
        for item in world.knowledge_item_repo.list_by_business(world.business.id)
        if str(item.title) == title
    )
    assert all(alias.status is SUGGESTED for alias in item.aliases)
    return {str(alias.language): str(alias.text) for alias in item.aliases}


def test_one_call_names_every_confirmed_active_item_and_records_its_cost() -> None:
    world = CrossLanguageWorld()
    khachapuri = world.add_item(
        "Adjarian khachapuri", kind=KnowledgeItemKind.MENU_ITEM, price_minor=1800
    )
    parking = world.add_item("Do you have parking?")
    world.add_item("Can I come with children?", is_active=False)
    # An import's draft: switched off until the owner confirms it.
    draft = world.add_item("When is the live music?", is_active=False)
    world.knowledge_item_repo.save(
        draft.model_copy(update={"import_batch_id": MenuImportBatchId()})
    )

    report = world.run_index()

    [request] = world.suggester.requests
    # Questions first: they become starter questions.
    assert [str(item.title) for item in request.items] == [
        "Do you have parking?",
        "Adjarian khachapuri",
    ]
    assert [str(language) for language in request.items[0].target_languages] == [
        "ka",
        "ru",
        "he",
    ]
    assert aliases_of(world, "Do you have parking?") == {
        "ka": "გაქვთ პარკინგი?",
        "ru": "Есть ли парковка?",
        "he": "יש חניה?",
    }
    assert aliases_of(world, "Adjarian khachapuri")["ka"] == "აჭარული ხაჭაპური"
    # Suggestions change nothing the assistant's version holds.
    assert world.item(parking).updated_at == parking.updated_at
    assert world.item(khachapuri).updated_at == khachapuri.updated_at
    usage = world.usage_event_repo.list_by_business_between(
        world.business.id, Microseconds(0), Microseconds(2**62)
    )
    assert {event.kind for event in usage} == {
        UsageKind.LLM_INPUT_TOKENS,
        UsageKind.LLM_OUTPUT_TOKENS,
    }
    # Both active, confirmed items have a vector; the draft and the
    # switched-off item have none.
    assert set(world.embedding_store.read_fingerprints(world.business.id)) == {
        parking.id,
        khachapuri.id,
    }
    assert int(report.processed_count) == 4


def test_a_second_run_over_unchanged_knowledge_costs_nothing() -> None:
    world = CrossLanguageWorld()
    world.add_item("Do you have parking?")
    world.run_index()
    calls_before = len(world.embedder.calls)

    world.run_index()

    assert len(world.suggester.requests) == 1
    assert len(world.embedder.calls) == calls_before


def test_a_changed_item_is_embedded_again_and_a_deleted_one_forgotten() -> None:
    world = CrossLanguageWorld(languages=("en",))
    parking = world.add_item("Do you have parking?", body="Next door.")
    children = world.add_item("Can I come with children?")
    world.run_index()
    world.knowledge_item_repo.save(
        world.item(parking).model_copy(
            update={"body": KnowledgeBody("Free parking for guests.")}
        )
    )
    world.knowledge_item_repo.delete(world.business.id, children.id)

    world.run_index()

    assert world.suggester.requests == []
    assert len(world.embedder.calls[-1]) == 1
    assert "Free parking for guests." in world.embedder.calls[-1][0]
    assert set(world.embedding_store.read_fingerprints(world.business.id)) == {
        parking.id
    }


def test_a_big_knowledge_base_is_named_forty_items_a_call_five_calls_a_run() -> None:
    world = CrossLanguageWorld(languages=("en", "ka"))
    for number in range(230):
        world.add_item(f"Question number {number}?")

    world.run_index()

    assert [len(request.items) for request in world.suggester.requests] == [40] * 5


def test_a_failed_alias_call_still_refreshes_vectors_and_the_job_is_retried() -> None:
    world = CrossLanguageWorld()
    parking = world.add_item("Do you have parking?")
    world.suggester.failure = ExternalServiceError("Model unavailable.")

    with pytest.raises(ExternalServiceError):
        world.run_index()

    assert set(world.embedding_store.read_fingerprints(world.business.id)) == {
        parking.id
    }
    report = world.run_index(is_final_attempt=True)
    assert int(report.processed_count) == 0
    assert world.item(parking).aliases == []
