"""The website chat widget script and its demo page (static, no business data)."""

import hashlib
import html
from pathlib import Path
from string import Template
from typing import Annotated

from fastapi import APIRouter, Header, Query, Response, status
from fastapi.responses import HTMLResponse

from app.gateways.http.strict_request_parsing import parse_path_identifier
from app.schemas.constants.channels import WidgetPosition
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetAccentColor
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_endpoints import (
    WIDGET_BUSINESS_ATTRIBUTE,
    WIDGET_DEMO_PATH,
    WIDGET_SCRIPT_PATH,
)

STATIC_DIRECTORY: Path = Path(__file__).resolve().parent / "static"
WIDGET_SCRIPT_FILE_NAME: str = "widget.js"
WIDGET_DEMO_TEMPLATE_FILE_NAME: str = "widget_demo.html"
WIDGET_SCRIPT_MEDIA_TYPE: str = "text/javascript; charset=utf-8"
# The embed URL has no version, so browsers re-check the script every five
# minutes (a cheap 304 thanks to the ETag) and pick up a deploy quickly.
WIDGET_SCRIPT_HEADERS: dict[str, str] = {
    "Cache-Control": "public, max-age=300, stale-while-revalidate=86400",
    "Access-Control-Allow-Origin": "*",
    "Cross-Origin-Resource-Policy": "cross-origin",
    "X-Content-Type-Options": "nosniff",
}
# The demo page talks only to this API: its own script and the widget routes.
WIDGET_DEMO_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; connect-src 'self'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex",
}
# From /widget/demo the script is one level up, also behind a path prefix.
DEMO_SCRIPT_RELATIVE_URL: str = ".." + WIDGET_SCRIPT_PATH
DEMO_FORM_ACTION: str = WIDGET_DEMO_PATH.rsplit("/", 1)[-1]


def build_widget_script_router(static_directory: Path = STATIC_DIRECTORY) -> APIRouter:
    """
    Routes (public, no bearer token):
        GET /widget.js                       the chat widget (any site may load
                                             it; HEAD too)
        GET /widget/demo?business_id=...     a page that embeds the widget;
                                             optional `language` forces the
                                             interface language, `color`
                                             (hex) and `position` (left or
                                             right) preview unsaved choices

    The script is read once, when the router is built, and served with an
    ETag; the demo page shows the widget even while the chat is switched off
    (a preview for owners), so the widget can be checked before going live.
    """

    script_body: bytes = (static_directory / WIDGET_SCRIPT_FILE_NAME).read_bytes()
    script_etag: str = '"' + hashlib.sha256(script_body).hexdigest()[:32] + '"'
    demo_template = Template(
        (static_directory / WIDGET_DEMO_TEMPLATE_FILE_NAME).read_text(encoding="utf-8")
    )
    router = APIRouter(tags=["widget"])

    @router.api_route(
        WIDGET_SCRIPT_PATH,
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )
    def get_widget_script(
        if_none_match: Annotated[str | None, Header()] = None,
    ) -> Response:
        headers: dict[str, str] = {**WIDGET_SCRIPT_HEADERS, "ETag": script_etag}
        if if_none_match is not None and is_etag_matched(if_none_match, script_etag):
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

        return Response(
            content=script_body,
            media_type=WIDGET_SCRIPT_MEDIA_TYPE,
            headers=headers,
        )

    @router.get(WIDGET_DEMO_PATH, include_in_schema=False)
    def get_widget_demo(
        business_id: Annotated[str | None, Query()] = None,
        language: Annotated[str | None, Query()] = None,
        color: Annotated[str | None, Query()] = None,
        position: Annotated[str | None, Query()] = None,
    ) -> HTMLResponse:
        page: str
        if business_id is None or business_id.strip() == "":
            page = demo_template.substitute(content=render_business_form(), widget="")
        else:
            parsed_business_id: BusinessId = parse_path_identifier(
                business_id.strip(),
                BusinessId,
                "Chat",
            )
            page = demo_template.substitute(
                content=render_embed_code(parsed_business_id),
                widget=render_widget_tag(
                    parsed_business_id,
                    parse_language(language),
                    parse_accent_color(color),
                    parse_position(position),
                ),
            )

        return HTMLResponse(content=page, headers=WIDGET_DEMO_HEADERS)

    return router


def is_etag_matched(if_none_match: str, etag: str) -> bool:
    """If-None-Match lists ETags (weak or strong) or is "*"."""

    candidates: list[str] = [
        candidate.strip().removeprefix("W/") for candidate in if_none_match.split(",")
    ]
    return "*" in candidates or etag in candidates


def parse_language(raw_language: str | None) -> LanguageTag | None:
    """The demo's forced interface language; anything malformed is ignored."""

    if raw_language is None:
        return None

    try:
        return LanguageTag(raw_language.strip())
    except ValueError:
        return None


def parse_accent_color(raw_color: str | None) -> WidgetAccentColor | None:
    """A previewed brand colour ("#0f766e"); anything else is ignored."""

    if raw_color is None:
        return None

    try:
        return WidgetAccentColor(raw_color.strip())
    except ValueError:
        return None


def parse_position(raw_position: str | None) -> WidgetPosition | None:
    """A previewed launcher corner; anything else is ignored."""

    if raw_position is None:
        return None

    try:
        return WidgetPosition(raw_position.strip().lower())
    except ValueError:
        return None


def render_widget_tag(
    business_id: BusinessId,
    language: LanguageTag | None,
    color: WidgetAccentColor | None = None,
    position: WidgetPosition | None = None,
) -> str:
    """The embed tag of the cabinet snippet, plus the demo's preview options."""

    attributes: list[str] = [
        f'src="{html.escape(DEMO_SCRIPT_RELATIVE_URL, quote=True)}"',
        f'{WIDGET_BUSINESS_ATTRIBUTE}="{html.escape(str(business_id), quote=True)}"',
        'data-preview="true"',
        'data-open="true"',
    ]
    if language is not None:
        attributes.append(f'data-language="{html.escape(str(language), quote=True)}"')

    if color is not None:
        attributes.append(f'data-color="{html.escape(str(color), quote=True)}"')

    if position is not None:
        attributes.append(f'data-position="{position.value}"')

    return f"<script {' '.join(attributes)} async></script>"


def render_embed_code(business_id: BusinessId) -> str:
    snippet: str = (
        f'<script src="https://<your API address>{WIDGET_SCRIPT_PATH}" '
        f'{WIDGET_BUSINESS_ATTRIBUTE}="{business_id}" async></script>'
    )
    return (
        "  <section>\n"
        "    <h2>Embed code</h2>\n"
        "    <p>Paste it before the closing &lt;/body&gt; tag of every page of "
        "the website. The cabinet (Channels &rarr; Website chat) shows it with "
        "the right address.</p>\n"
        f"    <pre><code>{html.escape(snippet)}</code></pre>\n"
        "  </section>\n"
        "  <section>\n"
        "    <h2>Options</h2>\n"
        "    <ul>\n"
        '      <li><code>data-color="#0f766e"</code> &mdash; accent colour</li>\n'
        '      <li><code>data-position="left"</code> &mdash; launcher on the '
        "left</li>\n"
        '      <li><code>data-language="ka"</code> &mdash; interface '
        "language</li>\n"
        '      <li><code>data-open="true"</code> &mdash; open the chat on the '
        "first page of a visit</li>\n"
        "    </ul>\n"
        "  </section>\n"
    )


def render_business_form() -> str:
    return (
        "  <section>\n"
        f'    <form method="get" action="{html.escape(DEMO_FORM_ACTION)}">\n'
        '      <label for="business_id">Business id</label>\n'
        '      <input id="business_id" name="business_id" required '
        'placeholder="business_…" autocomplete="off">\n'
        '      <button type="submit">Show the widget</button>\n'
        "    </form>\n"
        "  </section>\n"
    )
