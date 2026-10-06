"""
Drafting missing owner texts with the language model: the English texts
go in batches as one JSON object, the answer comes back as the same keys
in the target language. An answer that drops or invents a `{placeholder}`,
is empty or is not JSON is refused key by key; the text stays missing (it
reads English) until a later run or a person fills it.

Drafts are never final: the script marks them for review, and a native
speaker confirms them with `translate_catalogs.py backend reviewed`.
"""

import json
from collections.abc import Iterator

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.localization import CabinetLanguage
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import OwnerTextKey
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.utilities.localization.text_catalog_files import placeholders

BATCH_SIZE: int = 40
MAX_OUTPUT_TOKENS: LlmMaxOutputTokens = LlmMaxOutputTokens(8000)
LANGUAGE_NAMES: dict[CabinetLanguage, str] = {
    CabinetLanguage.GEORGIAN: "Georgian",
    CabinetLanguage.RUSSIAN: "Russian",
    CabinetLanguage.ENGLISH: "English",
    CabinetLanguage.HEBREW: "Hebrew",
    CabinetLanguage.GERMAN: "German",
}
# How the cabinet of each language speaks to owners (the web dictionaries
# use the same words).
STYLE_NOTES: dict[CabinetLanguage, str] = {
    CabinetLanguage.GEORGIAN: "Address the owner politely (თქვენ).",
    CabinetLanguage.RUSSIAN: "Address the owner as «вы», lowercase.",
    CabinetLanguage.ENGLISH: "",
    CabinetLanguage.HEBREW: (
        "Address the owner in the plural imperative (בדקו, שלמו). The cabinet "
        "is «לוח הבקרה», the plan and billing page «מסלול וחיוב», the "
        "assistant «העוזר»."
    ),
    CabinetLanguage.GERMAN: (
        "Address the owner formally (Sie). The cabinet is «Dashboard», the "
        "plan and billing page «Tarif und Abrechnung», the assistant «der "
        "Assistent»."
    ),
}
SYSTEM_PROMPT: str = (
    "You translate the owner-facing texts of Assistant Workshop, an AI "
    "front-line assistant that answers a small business's customers in "
    "chats and calls. The readers are the business owner and their staff: "
    "in the cabinet, in notifications and on invoices.\n\n"
    "Translate every value of the JSON object the user sends from English "
    "into {language}. {style}\n"
    "Keep every {{placeholder}} in curly braces exactly as it is, keep brand "
    "names (Telegram, WhatsApp, Magti), dial codes such as **61*{{number}}# "
    "and line breaks. Keep the tone short and plain.\n"
    "Answer with one JSON object with the same keys and the translated "
    "values, and nothing else."
)


class DraftedTexts(ImmutableDTO):
    """Texts the model drafted and the keys whose answer was refused."""

    drafts: dict[OwnerTextKey, LocalizedTextValue] = Field(
        default_factory=dict[OwnerTextKey, LocalizedTextValue]
    )
    refused: list[OwnerTextKey] = Field(default_factory=list[OwnerTextKey])


class OwnerTextDrafter:
    """Asks the language model for drafts of missing catalog texts."""

    def __init__(self, adapter: LlmAdapterContract, model_id: LlmModelId) -> None:
        self._adapter: LlmAdapterContract = adapter
        self._model_id: LlmModelId = model_id

    def draft(
        self,
        language: CabinetLanguage,
        english: dict[OwnerTextKey, LocalizedTextValue],
    ) -> DraftedTexts:
        drafts: dict[OwnerTextKey, LocalizedTextValue] = {}
        refused: list[OwnerTextKey] = []
        for batch in batches(english):
            answer: dict[str, object] = self.ask(language, batch)
            for key, source in batch.items():
                value: object = answer.get(str(key))
                if accepted(value, source):
                    drafts[key] = LocalizedTextValue(str(value))
                else:
                    refused.append(key)

        return DraftedTexts(drafts=drafts, refused=refused)

    def ask(
        self,
        language: CabinetLanguage,
        batch: dict[OwnerTextKey, LocalizedTextValue],
    ) -> dict[str, object]:
        """The model's answer as a JSON object; empty when it is not one."""

        question: str = json.dumps(
            {str(key): str(value) for key, value in batch.items()},
            ensure_ascii=False,
            indent=2,
        )
        response: LlmResponse = self._adapter.complete(
            LlmRequest(
                model_id=self._model_id,
                system_prompt=SystemPromptText(
                    SYSTEM_PROMPT.format(
                        language=LANGUAGE_NAMES[language], style=STYLE_NOTES[language]
                    )
                ),
                tools=[],
                transcript=[self._adapter.build_user_text_turn(MessageText(question))],
                max_output_tokens=MAX_OUTPUT_TOKENS,
                effort=LlmEffort.LOW,
            )
        )
        return parse_answer(None if response.text is None else str(response.text))


def batches(
    texts: dict[OwnerTextKey, LocalizedTextValue],
) -> Iterator[dict[OwnerTextKey, LocalizedTextValue]]:
    items: list[tuple[OwnerTextKey, LocalizedTextValue]] = list(texts.items())
    for start in range(0, len(items), BATCH_SIZE):
        yield dict(items[start : start + BATCH_SIZE])


def parse_answer(text: str | None) -> dict[str, object]:
    """The JSON object of an answer, with or without a Markdown code fence."""

    if text is None:
        return {}

    body: str = text.strip()
    if body.startswith("```"):
        body = body.strip("`").removeprefix("json").strip()
    try:
        answer: object = json.loads(body)
    except json.JSONDecodeError:
        return {}

    return answer if isinstance(answer, dict) else {}


def accepted(value: object, source: LocalizedTextValue) -> bool:
    """A non-empty string with exactly the placeholders of the English text."""

    return (
        isinstance(value, str)
        and value.strip() != ""
        and placeholders(LocalizedTextValue(value)) == placeholders(source)
    )
