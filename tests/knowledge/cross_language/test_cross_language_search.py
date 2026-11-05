"""
A question in Georgian, Russian or Hebrew finds an English-titled item: by
the item's aliases (lexical, no key needed) and by meaning (hybrid search
with embeddings), and the search stays lexical when embeddings fail.
"""

from app.adapters.embeddings.disabled_text_embedder_adapter import (
    DisabledTextEmbedderAdapter,
)
from app.schemas.constants.knowledge import KnowledgeAliasStatus, KnowledgeItemKind
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.knowledge.constrained_strings import EmbeddingModelId
from app.use_cases.knowledge.knowledge_embedding_refresh import refresh_embeddings
from app.use_cases.knowledge.knowledge_search_choice import choose_knowledge_search
from tests.knowledge.cross_language.world import CrossLanguageWorld

APPROVED = KnowledgeAliasStatus.APPROVED
SUGGESTED = KnowledgeAliasStatus.SUGGESTED
PARKING = "Do you have parking?"
CHILDREN = "Can I come with children?"
MUSIC = "When is the live music?"


def world_with_aliases() -> CrossLanguageWorld:
    world = CrossLanguageWorld()
    world.add_item(
        PARKING,
        body="No own parking; the city lot on Kote Abkhazi street is next door.",
        aliases=[
            ("ka", "გაქვთ პარკინგი?", APPROVED),
            ("ru", "Есть ли парковка?", APPROVED),
            ("he", "יש חניה?", SUGGESTED),
        ],
    )
    world.add_item(
        CHILDREN,
        body="Yes: high chairs, a kids' menu and a closed yard.",
        aliases=[
            ("ka", "შეიძლება ბავშვებთან ერთად მოსვლა?", APPROVED),
            ("ru", "Можно ли прийти с детьми?", APPROVED),
            ("he", "אפשר לבוא עם ילדים?", APPROVED),
        ],
    )
    world.add_item(
        MUSIC,
        body="Fridays and Saturdays from 20:00.",
        aliases=[
            ("ka", "როდის არის ცოცხალი მუსიკა?", APPROVED),
            ("ru", "Когда у вас живая музыка?", SUGGESTED),
            ("he", "מתי יש מוזיקה חיה?", APPROVED),
        ],
    )
    return world


def test_aliases_let_georgian_russian_and_hebrew_questions_find_english_titles() -> (
    None
):
    world = world_with_aliases()

    assert world.search("პარკინგი გაქვთ?", "ka", hybrid=False)[0] == PARKING
    assert world.search("а парковка у вас есть", "ru", hybrid=False)[0] == PARKING
    assert world.search("יש לכם חניה?", "he", hybrid=False)[0] == PARKING
    assert world.search("ბავშვებთან ერთად", "ka", hybrid=False)[0] == CHILDREN
    assert world.search("можно с детьми?", "ru", hybrid=False)[0] == CHILDREN
    assert world.search("עם ילדים", "he", hybrid=False)[0] == CHILDREN
    # A suggestion nobody reviewed yet is searched all the same.
    assert world.search("живая музыка", "ru", hybrid=False)[0] == MUSIC
    assert world.search("מוזיקה חיה", "he", hybrid=False)[0] == MUSIC


def test_meaning_finds_english_titles_that_have_no_alias_yet() -> None:
    world = CrossLanguageWorld()
    items = [
        world.add_item(PARKING, body="The city lot is next door."),
        world.add_item(CHILDREN, body="High chairs and a kids' menu."),
        world.add_item(
            "Payment", kind=KnowledgeItemKind.POLICY, body="Visa, Mastercard, cash."
        ),
    ]
    refresh_embeddings(world.embedder, world.embedding_store, world.business.id, items)
    questions = {
        "ka": "სად დავტოვო მანქანა?",
        "ru": "Где оставить машину?",
        "he": "איפה להשאיר את הרכב?",
    }

    for language, question in questions.items():
        assert world.search(question, language, hybrid=False) == []
        assert world.search(question, language)[0] == PARKING

    assert world.search("ბარათით გადახდა შეიძლება?", "ka")[0] == "Payment"
    assert world.search("можно оплатить картой?", "ru")[0] == "Payment"
    assert world.search("אפשר לשלם בכרטיס?", "he")[0] == "Payment"
    assert world.search("а детям можно?", "ru")[0] == CHILDREN


def test_both_sides_agreeing_rank_first_and_unrelated_meanings_stay_out() -> None:
    world = world_with_aliases()
    items = world.knowledge_item_repo.list_by_business(world.business.id)
    refresh_embeddings(world.embedder, world.embedding_store, world.business.id, items)

    found = world.search("парковка для машины", "ru")

    assert found == [PARKING]


def test_search_stays_lexical_when_the_embeddings_endpoint_fails() -> None:
    world = world_with_aliases()
    items = world.knowledge_item_repo.list_by_business(world.business.id)
    refresh_embeddings(world.embedder, world.embedding_store, world.business.id, items)
    world.embedder.failure = ExternalServiceError("Embeddings timed out.")

    assert world.search("Есть ли парковка?", "ru")[0] == PARKING
    assert world.search("Где оставить машину?", "ru") == []


def test_vectors_of_switched_off_or_deleted_items_are_never_returned() -> None:
    world = CrossLanguageWorld()
    parking = world.add_item(PARKING)
    children = world.add_item(CHILDREN)
    refresh_embeddings(
        world.embedder, world.embedding_store, world.business.id, [parking, children]
    )
    world.knowledge_item_repo.save(parking.model_copy(update={"is_active": False}))
    world.knowledge_item_repo.delete(world.business.id, children.id)

    assert world.search("Где оставить машину?", "ru") == []
    assert world.search("а детям можно?", "ru") == []


def test_without_an_embeddings_key_the_tool_runs_the_lexical_search() -> None:
    world = CrossLanguageWorld()
    disabled = DisabledTextEmbedderAdapter(EmbeddingModelId("text-embedding-3-small"))

    assert (
        choose_knowledge_search(disabled, world.hybrid_search, world.lexical_search)
        is world.lexical_search
    )
    assert (
        choose_knowledge_search(
            world.embedder, world.hybrid_search, world.lexical_search
        )
        is world.hybrid_search
    )
