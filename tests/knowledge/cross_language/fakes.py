"""
Fakes of the cross-language search: an alias model that answers from a
phrase book, and an embedder whose vectors are concepts named in several
languages (so a Georgian, Russian or Hebrew question is close in meaning to
an English title, as a real multilingual model makes it).
"""

import math
import threading
from collections.abc import Callable, Mapping, Sequence

from app.contracts.knowledge_aliases import KnowledgeAliasSuggesterContract
from app.contracts.knowledge_embeddings import EmbeddingVector, TextEmbedderContract
from app.schemas.dto.knowledge_aliases import (
    AliasSuggestionRequest,
    AliasSuggestionResult,
    SuggestedAlias,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.knowledge.constrained_strings import (
    EmbeddingModelId,
    KnowledgeAliasText,
)
from app.schemas.typings.knowledge.strings import EmbeddingInputText
from app.utilities.knowledge.search_text import fold_text

# Title -> language -> how a customer says it there.
PHRASE_BOOK: dict[str, dict[str, str]] = {
    "Do you have parking?": {
        "ka": "გაქვთ პარკინგი?",
        "ru": "Есть ли парковка?",
        "he": "יש חניה?",
    },
    "Can I come with children?": {
        "ka": "შეიძლება ბავშვებთან ერთად მოსვლა?",
        "ru": "Можно ли прийти с детьми?",
        "he": "אפשר לבוא עם ילדים?",
    },
    "When is the live music?": {
        "ka": "როდის არის ცოცხალი მუსიკა?",
        "ru": "Когда у вас живая музыка?",
        "he": "מתי יש מוזיקה חיה?",
    },
    "Adjarian khachapuri": {
        "ka": "აჭარული ხაჭაპური",
        "ru": "Хачапури по-аджарски",
        "he": "חצ'פורי אג'רי",
    },
}

# Concept -> folded word stems that name it, in en, ka, ru and he.
CONCEPTS: dict[str, tuple[str, ...]] = {
    "parking": ("parking", "car", "პარკინგ", "მანქან", "парков", "машин", "חני", "רכב"),
    "children": ("child", "kid", "ბავშვ", "дет", "ребен", "ילד"),
    "music": ("music", "მუსიკ", "музык", "מוזיק"),
    "delivery": ("deliver", "მიტან", "доставк", "משלוח"),
    "payment": ("pay", "card", "გადახდ", "ბარათ", "оплат", "карт", "תשלום", "כרטיס"),
    "khachapuri": ("khachapuri", "ხაჭაპურ", "хачапури", "חצ'פורי"),
}
CONCEPT_NAMES: list[str] = list(CONCEPTS)


class PhraseBookAliasSuggester(KnowledgeAliasSuggesterContract):
    """Answers every asked language the phrase book knows; counts its calls."""

    def __init__(
        self,
        phrase_book: Mapping[str, Mapping[str, str]] = PHRASE_BOOK,
        before_answer: Callable[[AliasSuggestionRequest], None] | None = None,
        failure: ExternalServiceError | None = None,
    ) -> None:
        self._phrase_book: Mapping[str, Mapping[str, str]] = phrase_book
        self._before_answer: Callable[[AliasSuggestionRequest], None] | None = (
            before_answer
        )
        self.failure: ExternalServiceError | None = failure
        self.requests: list[AliasSuggestionRequest] = []

    def suggest(self, request: AliasSuggestionRequest) -> AliasSuggestionResult:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure

        if self._before_answer is not None:
            self._before_answer(request)

        aliases: list[SuggestedAlias] = [
            SuggestedAlias(
                item_id=item.item_id,
                language=language,
                text=KnowledgeAliasText(
                    self._phrase_book[str(item.title)][str(language)]
                ),
            )
            for item in request.items
            for language in item.target_languages
            if str(language) in self._phrase_book.get(str(item.title), {})
        ]
        return AliasSuggestionResult(
            aliases=aliases,
            model_id=LlmModelId("gpt-5-mini"),
            input_tokens=LlmTokenCount(120 * len(request.items)),
            output_tokens=LlmTokenCount(30 * len(aliases)),
        )


class ConceptEmbedder(TextEmbedderContract):
    """
    One dimension per concept: a text's vector counts the concept's stems in
    it (plus a small constant, so an unrelated text is not a zero vector).
    """

    def __init__(self, model_id: str = "concept-embedding-1") -> None:
        self._model_id: EmbeddingModelId = EmbeddingModelId(model_id)
        self._lock: threading.Lock = threading.Lock()
        self.calls: list[list[str]] = []
        self.failure: ExternalServiceError | None = None

    def is_enabled(self) -> bool:
        return True

    def model_id(self) -> EmbeddingModelId:
        return self._model_id

    def embed(self, texts: Sequence[EmbeddingInputText]) -> list[EmbeddingVector]:
        with self._lock:
            self.calls.append([str(text) for text in texts])
        if self.failure is not None:
            raise self.failure

        return [concept_vector(str(text)) for text in texts]


def concept_vector(text: str) -> EmbeddingVector:
    folded: str = fold_text(text)
    counts: list[float] = [
        float(sum(folded.count(stem) for stem in CONCEPTS[name])) + 0.05
        for name in CONCEPT_NAMES
    ]
    norm: float = math.sqrt(sum(value * value for value in counts))
    return tuple(value / norm for value in counts)
