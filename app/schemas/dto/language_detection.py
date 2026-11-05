from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.localization.booleans import IsLanguageReadFromText
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)


class DetectedLanguage(ImmutableDTO):
    """
    The language a customer message is written in, any BCP 47 tag.

    `script_hint` is set when the customer writes the language in another
    script than its own, e.g. Georgian in Latin letters ("gamarjoba"):
    "Latn" for `language` "ka". `is_read_from_text` is False when the text
    told nothing (an emoji, "ok", a number) or too little to switch, and the
    conversation's, the contact's or the business's default language was
    kept.
    """

    language: LanguageTag
    script_hint: ScriptCode | None = None
    is_read_from_text: IsLanguageReadFromText
