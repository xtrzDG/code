"""Small help centers written to a temporary folder, and a clock for the progress."""

from pathlib import Path

from typed_time_provider import Microseconds, WallClock

from app.registries.help.help_article_registry import HelpArticleRegistry

NOW: Microseconds = Microseconds(1_790_000_000_000_000)


def article(
    title: str,
    summary: str = "What it answers.",
    topic: str = "channels",
    order: int = 10,
    keywords: str = "",
    related: str = "",
    body: str = "Some text.",
) -> str:
    lines: list[str] = ["---", f"summary: {summary}", f"topic: {topic}"]
    lines.append(f"order: {order}")
    if keywords:
        lines.append(f"keywords: {keywords}")
    if related:
        lines.append(f"related: {related}")
    return "\n".join([*lines, "---", f"# {title}", "", body, ""])


def write_help(root: Path, files: dict[str, dict[str, str]]) -> Path:
    """`files` maps a language folder to its {slug: text}."""

    for language, articles in files.items():
        folder: Path = root / language
        folder.mkdir(parents=True, exist_ok=True)
        for slug, text in articles.items():
            (folder / f"{slug}.md").write_text(text, encoding="utf-8")
    return root


def two_language_registry(root: Path) -> HelpArticleRegistry:
    return HelpArticleRegistry(
        write_help(
            root,
            {
                "en": {
                    "telegram": article(
                        "Telegram",
                        keywords="bot, token",
                        related="whatsapp, missing",
                        body="Open @BotFather and send /newbot. Paste the token.",
                    ),
                    "whatsapp": article("WhatsApp", order=20, body="Meta checks it."),
                    "getting-started": article(
                        "Getting started", topic="getting_started", body="Begin."
                    ),
                },
                "ru": {
                    "telegram": article(
                        "Телеграм",
                        keywords="бот, токен",
                        body="Откройте @BotFather и отправьте /newbot.",
                    ),
                    "whatsapp": article("Ватсап", order=20),
                    "getting-started": article("Как начать", topic="getting_started"),
                },
            },
        )
    )


class Clock:
    def __init__(self, start: Microseconds = NOW) -> None:
        self.now: int = int(start)
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.now * 1_000,
        )

    def advance(self, microseconds: int) -> None:
        self.now += microseconds
