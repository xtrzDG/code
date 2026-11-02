"""
A staff notification as an e-mail: the first line is the subject, the text
is the plain body, and the HTML body shows the title, the lines and the
cabinet link as a button. Every value is escaped; `dir="auto"` lays right
to left scripts out correctly. The subject is a header, so every control
character in it (a lone CR, a vertical tab, a line or paragraph separator)
becomes a space: a customer's name can never start a new header.
"""

import html
import re
import unicodedata
from dataclasses import dataclass

from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.messaging.strings import EmailBodyText, EmailSubject

MAX_SUBJECT_LENGTH: int = 150
# "<label>: <link>" as the last line (the link line of every notification).
LINK_LINE: re.Pattern[str] = re.compile(
    r"^(?P<label>[^:]{1,40}):\s+(?P<url>https?://\S+)$"
)
# Unicode categories that may not stay in a header value: controls
# (CR, LF, NUL, ...), line and paragraph separators.
HEADER_BREAKING_CATEGORIES: frozenset[str] = frozenset({"Cc", "Zl", "Zp"})
ACCENT_COLOR: str = "#7c5cff"
FOOTER: str = "Assistant Workshop"


@dataclass(frozen=True)
class StaffEmail:
    subject: EmailSubject
    text_body: EmailBodyText
    html_body: EmailBodyText


def build_staff_email(text: MessageText) -> StaffEmail:
    lines: list[str] = [line for line in str(text).split("\n") if line.strip()]
    subject: str = header_value(lines[0]) if lines else ""
    if subject == "":
        subject = FOOTER
    if len(subject) > MAX_SUBJECT_LENGTH:
        subject = subject[: MAX_SUBJECT_LENGTH - 1].rstrip() + "…"

    return StaffEmail(
        subject=EmailSubject(subject),
        text_body=EmailBodyText(f"{text}\n\n—\n{FOOTER}\n"),
        html_body=EmailBodyText(render_html(lines)),
    )


def header_value(text: str) -> str:
    """One header line: control characters become spaces, runs collapse."""

    cleaned: str = "".join(
        " "
        if unicodedata.category(character) in HEADER_BREAKING_CATEGORIES
        else character
        for character in text
    )
    return " ".join(cleaned.split())


def render_html(lines: list[str]) -> str:
    parts: list[str] = []
    for index, line in enumerate(lines):
        link = LINK_LINE.match(line.strip())
        if link is not None:
            parts.append(
                '<p style="margin:24px 0 8px"><a href="'
                + html.escape(link.group("url"), quote=True)
                + f'" style="display:inline-block;background:{ACCENT_COLOR};'
                "color:#ffffff;text-decoration:none;font-weight:600;"
                'padding:12px 20px;border-radius:10px">'
                + html.escape(link.group("label"))
                + "</a></p>"
            )
            continue

        style: str = (
            "margin:0 0 12px;font-size:20px;font-weight:700"
            if index == 0
            else "margin:0 0 8px;color:#374151"
        )
        parts.append(f'<p style="{style}">{html.escape(line)}</p>')

    return (
        '<!doctype html><html><body style="margin:0;padding:24px;'
        "font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;"
        'font-size:16px;line-height:1.5;color:#111827">'
        f'<div dir="auto" style="max-width:520px">{"".join(parts)}'
        '<p style="margin:32px 0 0;font-size:12px;color:#9ca3af">'
        f"{FOOTER}</p></div></body></html>"
    )
