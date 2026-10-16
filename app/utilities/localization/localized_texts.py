"""Building LocalizedText values for curated catalogs."""

from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue

REQUIRED_LANGUAGE_TAG: str = "en"


def build_localized_text(**texts_by_language: str) -> LocalizedText:
    """
    Build a text from keyword arguments named by language tag:
    `build_localized_text(en="Chat", ru="Чат", ka="ჩატი")`.

    Raises:
        ValueError: English is missing (it is the last fallback everywhere).
    """

    if REQUIRED_LANGUAGE_TAG not in texts_by_language:
        raise ValueError("A localized text needs an English value.")

    return LocalizedText(
        values={
            LanguageTag(language_tag.replace("_", "-")): LocalizedTextValue(text)
            for language_tag, text in texts_by_language.items()
        }
    )
