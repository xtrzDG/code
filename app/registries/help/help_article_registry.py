import threading
from pathlib import Path

from app.contracts.help import HelpArticleRegistryContract
from app.registries.help.help_article_files import read_help_directory
from app.registries.legal.legal_document_registry import select_translation
from app.schemas.dto.help import HelpArticleRecord
from app.schemas.typings.localization.constrained_strings import LanguageTag

# Repository root / docs / help; the backend image copies it to /app/docs/help.
DEFAULT_HELP_DIRECTORY: Path = Path(__file__).resolve().parents[3] / "docs" / "help"


class HelpArticleRegistry(HelpArticleRegistryContract):
    """
    The help center's articles, kept as Markdown in the repository:
    docs/help/<language>/<slug>.md (help_article_files.py has the format).
    Every language has the same slugs (a test keeps them in step). Files
    are read on first use and kept for the process.
    """

    def __init__(self, articles_directory: Path = DEFAULT_HELP_DIRECTORY) -> None:
        self._articles_directory: Path = articles_directory
        self._articles: dict[LanguageTag, list[HelpArticleRecord]] | None = None
        self._lock: threading.Lock = threading.Lock()

    def available_languages(self) -> list[LanguageTag]:
        return sorted(self._load(), key=str)

    def serve_language(self, requested: LanguageTag) -> LanguageTag | None:
        languages: list[LanguageTag] = list(self._load())
        if not languages:
            return None

        return select_translation(languages, requested)

    def list_articles(self, language: LanguageTag) -> list[HelpArticleRecord]:
        return list(self._load().get(language, []))

    def _load(self) -> dict[LanguageTag, list[HelpArticleRecord]]:
        with self._lock:
            if self._articles is None:
                self._articles = read_help_directory(self._articles_directory)

            return self._articles
