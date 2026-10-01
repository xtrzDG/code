import re
import threading
from pathlib import Path

from app.contracts.legal_registries import LegalDocumentRegistryContract
from app.schemas.dto.compliance import DpaDocumentView
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
from app.schemas.typings.compliance.strings import (
    LegalDocumentMarkdown,
    LegalDocumentTitle,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import (
    ENGLISH_LOCALE_IDENTIFIER,
    base_language_code,
    parse_language_tag,
)

# Repository root / docs / legal; the backend image copies it to /app/docs/legal.
DEFAULT_LEGAL_DOCUMENTS_DIRECTORY: Path = (
    Path(__file__).resolve().parents[3] / "docs" / "legal"
)
DPA_FILE_PATTERN: re.Pattern[str] = re.compile(
    r"^dpa-(?P<version>[0-9A-Za-z][0-9A-Za-z.\-_]*)\.(?P<language>[A-Za-z]{2,3}"
    r"(?:-[A-Za-z0-9]{2,8})*)\.md$"
)
TITLE_PATTERN: re.Pattern[str] = re.compile(r"^#\s+(?P<title>.+?)\s*#*\s*$")


class LegalDocumentRegistry(LegalDocumentRegistryContract):
    """
    Data processing agreements kept as Markdown files in the repository,
    one file per version and language: `dpa-<version>.<language>.md` (for
    example `docs/legal/dpa-2026-10-01.ka.md`). The first `# ` heading is
    the title. Files are read on first use and kept for the process.
    """

    def __init__(
        self,
        documents_directory: Path = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    ) -> None:
        self._documents_directory: Path = documents_directory
        self._texts: dict[DpaDocumentVersion, dict[LanguageTag, str]] | None = None
        self._lock: threading.Lock = threading.Lock()

    def find_dpa(
        self,
        version: DpaDocumentVersion,
        language: LanguageTag,
    ) -> DpaDocumentView | None:
        translations: dict[LanguageTag, str] = self._load().get(version, {})
        if translations == {}:
            return None

        served: LanguageTag = select_translation(list(translations), language)
        text: str = translations[served]
        return DpaDocumentView(
            version=version,
            language=served,
            available_languages=sorted(translations, key=str),
            title=LegalDocumentTitle(read_title(text) or f"DPA {version}"),
            text=LegalDocumentMarkdown(text),
        )

    def _load(self) -> dict[DpaDocumentVersion, dict[LanguageTag, str]]:
        with self._lock:
            if self._texts is None:
                self._texts = read_dpa_files(self._documents_directory)

            return self._texts


def read_dpa_files(
    directory: Path,
) -> dict[DpaDocumentVersion, dict[LanguageTag, str]]:
    texts: dict[DpaDocumentVersion, dict[LanguageTag, str]] = {}
    if not directory.is_dir():
        return texts

    for path in sorted(directory.iterdir()):
        match: re.Match[str] | None = DPA_FILE_PATTERN.match(path.name)
        if match is None or not path.is_file():
            continue

        version = DpaDocumentVersion(match.group("version"))
        language: LanguageTag = parse_language_tag(match.group("language"))
        texts.setdefault(version, {})[language] = path.read_text(encoding="utf-8")

    return texts


def select_translation(
    available: list[LanguageTag],
    requested: LanguageTag,
) -> LanguageTag:
    """Requested tag, else its base language, else English, else the first."""

    if requested in available:
        return requested

    base: str = base_language_code(requested)
    for candidate in (base, ENGLISH_LOCALE_IDENTIFIER):
        for language in available:
            if str(language) == candidate:
                return language

    for language in available:
        if base_language_code(language) == base:
            return language

    return sorted(available, key=str)[0]


def read_title(text: str) -> str | None:
    for line in text.splitlines():
        match: re.Match[str] | None = TITLE_PATTERN.match(line.strip())
        if match is not None:
            return match.group("title")

    return None
