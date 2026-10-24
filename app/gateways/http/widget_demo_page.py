"""The body of the website chat demo page (/widget/demo) in the reader's language."""

import html

from app.gateways.http.language_negotiation import negotiate_language
from app.gateways.http.widget_demo_texts import (
    DEFAULT_DEMO_LANGUAGE,
    WIDGET_DEMO_TEXTS,
    WidgetDemoTexts,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_endpoints import (
    WIDGET_BUSINESS_ATTRIBUTE,
    WIDGET_SCRIPT_PATH,
)

# The example of `data-color`: the widget's own clay accent (widget.js).
EXAMPLE_ACCENT_COLOR: str = "#ad5732"


def demo_page_language(
    forced_language: LanguageTag | None, accept_language: str | None
) -> str:
    """
    The page's language: the widget's forced language when the page has it,
    else the browser's preferred one, else English.
    """

    for candidate in (forced_language, negotiate_language(accept_language)):
        if candidate is None:
            continue

        base: str = str(candidate).split("-", 1)[0].lower()
        if base in WIDGET_DEMO_TEXTS:
            return base

    return DEFAULT_DEMO_LANGUAGE


def demo_page_fields(language: str, content: str, widget: str) -> dict[str, str]:
    """The template fields of the page (texts escaped, markup as given)."""

    texts: WidgetDemoTexts = WIDGET_DEMO_TEXTS[language]
    return {
        "lang": language,
        "title": html.escape(texts.title),
        "heading": html.escape(texts.heading),
        "intro": html.escape(texts.intro),
        "content": content,
        "widget": widget,
    }


def render_embed_code(business_id: BusinessId, language: str) -> str:
    texts: WidgetDemoTexts = WIDGET_DEMO_TEXTS[language]
    snippet: str = (
        f'<script src="https://{texts.api_address}{WIDGET_SCRIPT_PATH}" '
        f'{WIDGET_BUSINESS_ATTRIBUTE}="{business_id}" async></script>'
    )
    options: list[tuple[str, str]] = [
        (f'data-color="{EXAMPLE_ACCENT_COLOR}"', texts.option_color),
        ('data-position="left"', texts.option_position),
        ('data-language="ka"', texts.option_language),
        ('data-open="true"', texts.option_open),
        ('data-mode="page"', texts.option_mode),
    ]
    items: str = "".join(
        f"      <li><code>{html.escape(code)}</code> &mdash; "
        f"{html.escape(meaning)}</li>\n"
        for code, meaning in options
    )
    return (
        "  <section>\n"
        f"    <h2>{html.escape(texts.embed_title)}</h2>\n"
        f"    <p>{html.escape(texts.embed_body)}</p>\n"
        f"    <pre><code>{html.escape(snippet)}</code></pre>\n"
        "  </section>\n"
        "  <section>\n"
        f"    <h2>{html.escape(texts.options_title)}</h2>\n"
        "    <ul>\n"
        f"{items}"
        "    </ul>\n"
        "  </section>\n"
    )


def render_business_form(form_action: str, language: str) -> str:
    texts: WidgetDemoTexts = WIDGET_DEMO_TEXTS[language]
    return (
        "  <section>\n"
        f'    <form method="get" action="{html.escape(form_action)}">\n'
        f'      <label for="business_id">{html.escape(texts.business_id_label)}'
        "</label>\n"
        '      <input id="business_id" name="business_id" required '
        'placeholder="business_…" autocomplete="off">\n'
        f'      <button type="submit">{html.escape(texts.show_button)}</button>\n'
        "    </form>\n"
        "  </section>\n"
    )
