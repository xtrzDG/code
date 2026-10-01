from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import LocalizedTextValue
from app.utilities.localization.language_tags import split_language_tag_text

FALLBACK_LANGUAGE_CODE: str = "en"
SUBTAG_SEPARATOR: str = "-"


class LocalizedTextResolver(LocalizedTextResolverContract):
    """
    Pick the value of a LocalizedText for a requested language.

    Order (RFC 4647 lookup, then fallbacks):
    1. the exact tag, then the tag with trailing subtags removed
       ("zh-Hant-TW" -> "zh-Hant" -> "zh", "pt-BR" -> "pt");
    2. another variant of the same language ("pt-PT" for "pt-BR");
    3. English ("en", then any English variant);
    4. the first value in the text.
    """

    def resolve(
        self,
        text: LocalizedText,
        language_tag: LanguageTag,
    ) -> LocalizedTextValue:
        values_by_tag: dict[str, LocalizedTextValue] = {
            str(value_tag): value for value_tag, value in text.values.items()
        }
        if values_by_tag == {}:
            raise ValidationFailedError("Localized text has no values.")

        for candidate_tag in build_lookup_chain(str(language_tag)):
            exact_value: LocalizedTextValue | None = values_by_tag.get(candidate_tag)
            if exact_value is not None:
                return exact_value

        requested_language: str = split_language_tag_text(str(language_tag)).language
        for fallback_language in (requested_language, FALLBACK_LANGUAGE_CODE):
            fallback_value: LocalizedTextValue | None = values_by_tag.get(
                fallback_language
            )
            if fallback_value is not None:
                return fallback_value

            for value_tag, value in values_by_tag.items():
                if split_language_tag_text(value_tag).language == fallback_language:
                    return value

        return next(iter(values_by_tag.values()))


def build_lookup_chain(language_tag_text: str) -> list[str]:
    """Lookup chain of a tag: "zh-Hant-TW" -> "zh-Hant-TW", "zh-Hant", "zh"."""

    subtags: list[str] = language_tag_text.split(SUBTAG_SEPARATOR)
    return [
        SUBTAG_SEPARATOR.join(subtags[:subtag_count])
        for subtag_count in range(len(subtags), 0, -1)
    ]
