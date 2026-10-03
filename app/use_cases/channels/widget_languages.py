"""The website chat's customer languages and greetings, for its config."""

from collections.abc import Sequence

from app.contracts.registries import LanguageRegistryContract
from app.schemas.constants.localization import TextDirection
from app.schemas.dto.channels.widget import WidgetGreetingView, WidgetLanguageView
from app.schemas.dto.localization import LanguageProfile
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.strings import WidgetGreetingText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.widget_texts import build_widget_greeting


def find_language(
    language_registry: LanguageRegistryContract,
    language_tag: LanguageTag,
) -> LanguageProfile | None:
    try:
        return language_registry.get(language_tag)
    except UnsupportedLanguageError:
        return None


def build_widget_languages(
    language_registry: LanguageRegistryContract,
    languages: Sequence[LanguageTag],
) -> list[WidgetLanguageView]:
    """The languages with their native names and writing direction."""

    views: list[WidgetLanguageView] = []
    for language_tag in languages:
        profile: LanguageProfile | None = find_language(language_registry, language_tag)
        if profile is not None:
            views.append(
                WidgetLanguageView(
                    tag=language_tag,
                    native_name=profile.native_name,
                    direction=profile.direction,
                )
            )

    return views


def build_widget_greetings(
    language_registry: LanguageRegistryContract,
    languages: Sequence[LanguageTag],
    business_name: BusinessName,
) -> list[WidgetGreetingView]:
    """The first message in each language a text exists for."""

    greetings: list[WidgetGreetingView] = []
    for language_tag in languages:
        text: str | None = build_widget_greeting(language_tag, str(business_name))
        if text is None:
            continue

        profile: LanguageProfile | None = find_language(language_registry, language_tag)
        greetings.append(
            WidgetGreetingView(
                language=language_tag,
                text=WidgetGreetingText(text),
                direction=(
                    TextDirection.LEFT_TO_RIGHT
                    if profile is None
                    else profile.direction
                ),
            )
        )

    return greetings
