"""
The context line that names the customer's language for the model.

The platform reads the language of every customer message (any language,
also one the business did not list) and opens the first reply with the AI
disclosure in it, so the model is told which language that is, and how
the customer types it when it is transliterated.
"""

from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    ScriptCode,
)
from app.utilities.localization.cldr_language_names import (
    get_english_locale,
    read_locale_name,
)
from app.utilities.localization.display_names import (
    build_language_display_name_or_tag,
)
from app.utilities.localization.language_scripts import find_likely_script_code


def describe_reply_language(
    reply_language: LanguageTag,
    script_hint: ScriptCode | None,
) -> str:
    """
    "Reply language: Hebrew (he)." or, for a transliteration:

        Reply language: Georgian (ka). The customer types it in Latin
        letters; reply in Georgian script unless they ask for Latin letters.
    """

    language_name: str = str(
        build_language_display_name_or_tag(reply_language, get_english_locale())
    )
    line: str = f"Reply language: {language_name} ({reply_language})."
    if script_hint is None:
        return line

    typed_script: str = describe_script(str(script_hint))
    own_script: str = describe_script(find_likely_script_code(reply_language))
    return (
        f"{line} The customer types it in {typed_script} letters; reply in "
        f"{own_script} script unless they ask for {typed_script} letters."
    )


def describe_script(script_code: str) -> str:
    """English name of an ISO 15924 script, the code when CLDR has none."""

    return read_locale_name(get_english_locale().scripts, script_code) or script_code
