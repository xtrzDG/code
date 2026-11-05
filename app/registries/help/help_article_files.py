"""
Reading the help articles: docs/help/<language>/<slug>.md, each a front
matter of `key: value` lines between `---` lines, then the title as the
first `# ` heading, then the body in Markdown:

    ---
    summary: Forward missed calls to the assistant in one code.
    topic: channels
    order: 30
    keywords: call forwarding, operator, busy, missed calls
    related: getting-started, whatsapp
    ---
    # Call forwarding
    ...
"""

import re
from pathlib import Path

from app.schemas.constants.help import HelpTopic
from app.schemas.dto.help import HelpArticleRecord
from app.schemas.typings.help.constrained_integers import HelpArticleOrder
from app.schemas.typings.help.constrained_strings import HelpArticleSlug
from app.schemas.typings.help.strings import (
    HelpArticleMarkdown,
    HelpArticleSummary,
    HelpArticleTitle,
    HelpKeyword,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import parse_language_tag

FRONT_MATTER_DELIMITER: str = "---"
ARTICLE_FILE_PATTERN: re.Pattern[str] = re.compile(r"^(?P<slug>[a-z0-9-]+)\.md$")
LANGUAGE_DIRECTORY_PATTERN: re.Pattern[str] = re.compile(
    r"^[a-z]{2,3}(-[A-Za-z0-9]+)*$"
)
TITLE_PATTERN: re.Pattern[str] = re.compile(r"^#\s+(?P<title>.+?)\s*#*\s*$")
FIELD_PATTERN: re.Pattern[str] = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<value>.*)$")
DEFAULT_ORDER: int = 100


class HelpArticleFormatError(ValueError):
    """A help article file does not have the shape the registry reads."""


def read_help_directory(directory: Path) -> dict[LanguageTag, list[HelpArticleRecord]]:
    """Every language folder under `directory` and the articles in it."""

    articles: dict[LanguageTag, list[HelpArticleRecord]] = {}
    if not directory.is_dir():
        return articles

    for language_directory in sorted(directory.iterdir()):
        if not language_directory.is_dir():
            continue
        if LANGUAGE_DIRECTORY_PATTERN.match(language_directory.name) is None:
            continue

        language: LanguageTag = parse_language_tag(language_directory.name)
        records: list[HelpArticleRecord] = []
        for path in sorted(language_directory.iterdir()):
            match: re.Match[str] | None = ARTICLE_FILE_PATTERN.match(path.name)
            if match is None or not path.is_file():
                continue
            records.append(
                parse_article(
                    HelpArticleSlug(match.group("slug")),
                    language,
                    path.read_text(encoding="utf-8"),
                )
            )
        if records:
            articles[language] = records

    return articles


def parse_article(
    slug: HelpArticleSlug, language: LanguageTag, text: str
) -> HelpArticleRecord:
    fields, body = split_front_matter(text, slug)
    title, markdown = split_title(body, slug)
    summary: str = require_field(fields, "summary", slug)
    topic: str = require_field(fields, "topic", slug)
    if topic not in {member.value for member in HelpTopic}:
        raise HelpArticleFormatError(f"{slug}: unknown topic {topic!r}.")

    order_text: str = fields.get("order", str(DEFAULT_ORDER))
    if not order_text.isdigit():
        raise HelpArticleFormatError(f"{slug}: the order must be a number.")

    return HelpArticleRecord(
        slug=slug,
        language=language,
        title=HelpArticleTitle(title),
        summary=HelpArticleSummary(summary),
        topic=HelpTopic(topic),
        order=HelpArticleOrder(int(order_text)),
        keywords=[HelpKeyword(word) for word in split_list(fields.get("keywords"))],
        related=[
            HelpArticleSlug(related) for related in split_list(fields.get("related"))
        ],
        markdown=HelpArticleMarkdown(markdown),
    )


def split_front_matter(text: str, slug: str) -> tuple[dict[str, str], str]:
    lines: list[str] = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_DELIMITER:
        raise HelpArticleFormatError(f"{slug}: the file starts with front matter.")

    fields: dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONT_MATTER_DELIMITER:
            return fields, "\n".join(lines[index + 1 :])
        if not line.strip():
            continue
        match: re.Match[str] | None = FIELD_PATTERN.match(line.strip())
        if match is None:
            raise HelpArticleFormatError(f"{slug}: unreadable front matter {line!r}.")
        fields[match.group("key")] = match.group("value").strip()

    raise HelpArticleFormatError(f"{slug}: the front matter is not closed.")


def split_title(body: str, slug: str) -> tuple[str, str]:
    """The first `# ` heading and the Markdown after it."""

    lines: list[str] = body.splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        match: re.Match[str] | None = TITLE_PATTERN.match(line.strip())
        if match is None:
            break
        return match.group("title"), "\n".join(lines[index + 1 :]).strip() + "\n"

    raise HelpArticleFormatError(f"{slug}: the body starts with a '# ' title.")


def require_field(fields: dict[str, str], key: str, slug: str) -> str:
    value: str = fields.get(key, "")
    if not value:
        raise HelpArticleFormatError(f"{slug}: the front matter needs {key!r}.")
    return value


def split_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]
