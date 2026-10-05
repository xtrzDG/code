import re
import threading
from dataclasses import dataclass
from pathlib import Path

from typed_time_provider import Microseconds

from app.contracts.legal_text_registries import LegalTextRegistryContract
from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    read_title,
    select_translation,
)
from app.schemas.constants.legal import LegalDocumentKind
from app.schemas.dto.legal import LegalDocumentView
from app.schemas.typings.compliance.strings import (
    LegalDocumentMarkdown,
    LegalDocumentTitle,
)
from app.schemas.typings.legal.constrained_strings import LegalDocumentVersion
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.legal.subprocessor_dates import utc_day
from app.utilities.localization.language_tags import parse_language_tag

LEGAL_TEXT_FILE_PATTERN: re.Pattern[str] = re.compile(
    r"^(?P<kind>terms|privacy|cookies)-(?P<version>[0-9]{4}-[0-9]{2}-[0-9]{2})\."
    r"(?P<language>[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*)\.md$"
)
# "[Legal name of the operator]": a field to fill; "[text](url)" is a link.
PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\[[^\]\n]+\](?!\()")

type LegalTexts = dict[
    LegalDocumentKind, dict[LegalDocumentVersion, dict[LanguageTag, str]]
]


@dataclass(frozen=True)
class VersionChoice:
    served: LegalDocumentVersion
    upcoming: LegalDocumentVersion | None


class LegalTextRegistry(LegalTextRegistryContract):
    """
    The terms of service, the privacy policy and the cookie statement kept
    as Markdown in the repository, one file per version and language:
    `<kind>-<version>.<language>.md`, the version being the day the text
    takes effect (docs/legal/terms-2026-10-05.ka.md). The version in force
    is the newest one whose day has come (UTC); a file with a later day is
    published ahead and served as `upcoming_version`. Files are read on
    first use and kept for the process.
    """

    def __init__(
        self,
        documents_directory: Path = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
    ) -> None:
        self._documents_directory: Path = documents_directory
        self._texts: LegalTexts | None = None
        self._lock: threading.Lock = threading.Lock()

    def version_in_force(
        self, kind: LegalDocumentKind, now: Microseconds
    ) -> LegalDocumentVersion | None:
        today: str = utc_day(now).isoformat()
        started: list[LegalDocumentVersion] = [
            version for version in self._versions(kind) if str(version) <= today
        ]
        return started[-1] if started else None

    def has_version(
        self, kind: LegalDocumentKind, version: LegalDocumentVersion
    ) -> bool:
        return version in self._load().get(kind, {})

    def find(
        self,
        kind: LegalDocumentKind,
        version: LegalDocumentVersion | None,
        language: LanguageTag,
        now: Microseconds,
    ) -> LegalDocumentView | None:
        choice: VersionChoice | None = self._choose(kind, version, now)
        if choice is None:
            return None

        translations: dict[LanguageTag, str] = self._load()[kind][choice.served]
        served: LanguageTag = select_translation(list(translations), language)
        text: str = translations[served]
        return LegalDocumentView(
            kind=kind,
            version=choice.served,
            language=served,
            available_languages=sorted(translations, key=str),
            title=LegalDocumentTitle(read_title(text) or kind.value),
            text=LegalDocumentMarkdown(text),
            has_placeholders=PLACEHOLDER_PATTERN.search(text) is not None,
            upcoming_version=choice.upcoming,
        )

    def _choose(
        self,
        kind: LegalDocumentKind,
        version: LegalDocumentVersion | None,
        now: Microseconds,
    ) -> VersionChoice | None:
        in_force: LegalDocumentVersion | None = self.version_in_force(kind, now)
        later: list[LegalDocumentVersion] = [
            candidate
            for candidate in self._versions(kind)
            if in_force is None or str(candidate) > str(in_force)
        ]
        upcoming: LegalDocumentVersion | None = later[-1] if later else None
        served: LegalDocumentVersion | None = version or in_force
        if served is None or not self.has_version(kind, served):
            return None

        return VersionChoice(
            served=served, upcoming=None if upcoming == served else upcoming
        )

    def _versions(self, kind: LegalDocumentKind) -> list[LegalDocumentVersion]:
        return sorted(self._load().get(kind, {}), key=str)

    def _load(self) -> LegalTexts:
        with self._lock:
            if self._texts is None:
                self._texts = read_legal_text_files(self._documents_directory)

            return self._texts


def read_legal_text_files(directory: Path) -> LegalTexts:
    texts: LegalTexts = {}
    if not directory.is_dir():
        return texts

    for path in sorted(directory.iterdir()):
        match: re.Match[str] | None = LEGAL_TEXT_FILE_PATTERN.match(path.name)
        if match is None or not path.is_file():
            continue

        kind = LegalDocumentKind(match.group("kind"))
        version = LegalDocumentVersion(match.group("version"))
        language: LanguageTag = parse_language_tag(match.group("language"))
        texts.setdefault(kind, {}).setdefault(version, {})[language] = path.read_text(
            encoding="utf-8"
        )

    return texts
