"""The widget script's source and a parser of the script tags in a page."""

from html.parser import HTMLParser

from app.gateways.http.widget_script_assembly import assemble_widget_script
from app.gateways.http.widget_script_routes import STATIC_DIRECTORY

SCRIPT_SOURCE: str = assemble_widget_script(STATIC_DIRECTORY)
BUSINESS_ID: str = "business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01"


class ScriptTagParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.script_tags: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.script_tags.append(dict(attrs))


def parse_script_tags(markup: str) -> list[dict[str, str | None]]:
    parser = ScriptTagParser()
    parser.feed(markup)
    return parser.script_tags
