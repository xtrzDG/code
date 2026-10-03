"""Every hand-written source file stays small: at most 300 lines.

Many small files that each do a little and work together, instead of big
files with many functions. A file over the limit is split along its real
responsibilities (a use case and its helpers in a sub-package, data tables
in data modules), not cut at an arbitrary line.
"""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_SOURCE_FILE_LINES: int = 300
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
CABINET_SUFFIXES: frozenset[str] = frozenset({".ts", ".tsx", ".mts", ".css"})
# Checked folders (relative to the project root) and the suffixes of their
# source files. The widget's parts are assembled into /widget.js at startup.
# Tests follow the same rule: shared fixtures and fakes live in their own
# modules next to the test files that use them. The cabinet (web/) has the
# same limit in its ESLint config (max-lines) as well.
CHECKED_SOURCE_ROOTS: tuple[tuple[str, frozenset[str]], ...] = (
    ("app", frozenset({".py"})),
    ("scripts", frozenset({".py"})),
    ("app/gateways/http/static", frozenset({".js", ".html"})),
    ("tests", frozenset({".py"})),
    ("web/src", CABINET_SUFFIXES),
    ("web/e2e", CABINET_SUFFIXES),
)
# Not hand-written, or data rather than code: the generated API client and
# tables (`npm run gen:api`), and the translation dictionaries, which are
# split by section and language rather than by length.
EXEMPT_PATH_PATTERNS: tuple[str, ...] = (
    "web/src/api/schema.d.ts",
    "web/src/**/*.generated.ts",
    "web/src/i18n/messages/**",
)


@dataclass(frozen=True)
class OversizedFile:
    relative_path: str
    line_count: int


def test_source_files_have_at_most_300_lines() -> None:
    oversized_files: list[OversizedFile] = []
    for root_name, suffixes in CHECKED_SOURCE_ROOTS:
        oversized_files.extend(find_oversized_files(PROJECT_ROOT / root_name, suffixes))

    assert oversized_files == [], (
        f"Source files may have at most {MAX_SOURCE_FILE_LINES} lines. Split "
        "each file below along its responsibilities into smaller modules that "
        "work together (see docs/conventions.md); do not raise the limit.\n"
        + "\n".join(
            f"  {oversized.relative_path}: {oversized.line_count} lines"
            for oversized in oversized_files
        )
    )


def test_every_checked_root_has_source_files() -> None:
    # A renamed or moved folder must not make the size check pass vacuously.
    for root_name, suffixes in CHECKED_SOURCE_ROOTS:
        assert list_source_files(PROJECT_ROOT / root_name, suffixes) != [], root_name


def find_oversized_files(
    root_path: Path,
    suffixes: frozenset[str],
) -> list[OversizedFile]:
    oversized_files: list[OversizedFile] = []
    for file_path in list_source_files(root_path, suffixes):
        line_count: int = len(file_path.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_SOURCE_FILE_LINES:
            oversized_files.append(
                OversizedFile(
                    relative_path=file_path.relative_to(PROJECT_ROOT).as_posix(),
                    line_count=line_count,
                )
            )

    return oversized_files


def list_source_files(root_path: Path, suffixes: frozenset[str]) -> list[Path]:
    return sorted(
        file_path
        for file_path in root_path.rglob("*")
        if file_path.is_file()
        and file_path.suffix in suffixes
        and "__pycache__" not in file_path.parts
        and "node_modules" not in file_path.parts
        and not is_exempt(file_path)
    )


def is_exempt(file_path: Path) -> bool:
    relative_path = PurePosixPath(file_path.relative_to(PROJECT_ROOT).as_posix())
    return any(relative_path.full_match(pattern) for pattern in EXEMPT_PATH_PATTERNS)


def test_exempt_files_are_only_generated_files_and_dictionaries() -> None:
    assert is_exempt(PROJECT_ROOT / "web/src/api/schema.d.ts")
    assert is_exempt(PROJECT_ROOT / "web/src/lib/displayNames.generated.ts")
    assert is_exempt(PROJECT_ROOT / "web/src/i18n/messages/sections/settings/en.ts")
    assert not is_exempt(PROJECT_ROOT / "web/src/i18n/translate.ts")
    assert not is_exempt(PROJECT_ROOT / "web/src/api/client.ts")
    assert not is_exempt(PROJECT_ROOT / "app/main.py")
