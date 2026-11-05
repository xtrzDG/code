"""
The README is a short English entry and a map: every developer guide of
docs/dev/ is linked from it, it stays under 200 lines, and the relative
links of the README, the guides, the ADRs and SECURITY.md lead to files that
exist. Other documents point to the guides, not to README sections that
moved there.
"""

import re
import subprocess
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
README: Path = PROJECT_ROOT / "README.md"
DEVELOPER_GUIDES: Path = PROJECT_ROOT / "docs" / "dev"
ADR_DIRECTORY: Path = PROJECT_ROOT / "docs" / "adr"
README_MAX_LINES: int = 200
# [text](target) with a relative target; anchors and external links aside.
MARKDOWN_LINK: re.Pattern[str] = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s]+)\)")
CYRILLIC: re.Pattern[str] = re.compile(r"[Ѐ-ӿ]")
SECURITY_POLICY: Path = PROJECT_ROOT / "SECURITY.md"
# `(README, "Section")` or `README.md, "Section"` without a directory: a
# section of the root README.
ROOT_README_SECTION: re.Pattern[str] = re.compile(
    r'(?<![\w/.-])README(?:\.md)?,? "([^"]+)"'
)
ROOT_README_POINTER: re.Pattern[str] = re.compile(r"\broot README\b")
MARKDOWN_HEADING: re.Pattern[str] = re.compile(r"^#+ (.+)$", re.MULTILINE)


def developer_guides() -> list[Path]:
    return sorted(DEVELOPER_GUIDES.glob("*.md"))


def adr_files() -> list[Path]:
    return sorted(ADR_DIRECTORY.glob("[0-9][0-9][0-9][0-9]-*.md"))


def relative_links(document: Path) -> list[str]:
    return MARKDOWN_LINK.findall(document.read_text(encoding="utf-8"))


def test_the_readme_links_every_developer_guide() -> None:
    linked: set[Path] = {
        (README.parent / target.split("#", 1)[0]).resolve()
        for target in relative_links(README)
    }

    assert len(developer_guides()) >= 8
    assert [
        guide.relative_to(PROJECT_ROOT).as_posix()
        for guide in developer_guides()
        if guide.resolve() not in linked
    ] == []


def test_the_readme_stays_a_short_english_entry() -> None:
    text: str = README.read_text(encoding="utf-8")

    assert len(text.splitlines()) < README_MAX_LINES
    for command in ("just setup", "just dev", "just check"):
        assert command in text, command
    assert CYRILLIC.search(text) is None


def test_the_developer_guides_are_in_english() -> None:
    # Cyrillic appears only as quoted product strings, never as prose.
    russian: list[str] = [
        guide.relative_to(PROJECT_ROOT).as_posix()
        for guide in developer_guides()
        if len(CYRILLIC.findall(guide.read_text(encoding="utf-8"))) > 20
    ]

    assert russian == []


def test_every_relative_link_of_the_entry_guides_and_adrs_exists() -> None:
    broken: list[str] = [
        f"{document.relative_to(PROJECT_ROOT).as_posix()} -> {target}"
        for document in (
            README,
            SECURITY_POLICY,
            *developer_guides(),
            *adr_files(),
        )
        for target in relative_links(document)
        if not (document.parent / target.split("#", 1)[0]).exists()
    ]

    assert broken == []


def test_every_adr_is_in_the_index_with_its_number() -> None:
    index: str = (ADR_DIRECTORY / "README.md").read_text(encoding="utf-8")
    numbers: list[str] = [path.name[:4] for path in adr_files()]

    assert numbers == [f"{number:04d}" for number in range(1, len(numbers) + 1)]
    assert [path.name for path in adr_files() if f"]({path.name})" not in index] == []
    for path in adr_files():
        assert path.read_text(encoding="utf-8").startswith(f"# {path.name[:4]}. ")


def tracked_documents() -> list[Path]:
    listed: str = subprocess.run(
        ["git", "ls-files", "*.md", "*.py", "*.yml", "*.yaml"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [
        PROJECT_ROOT / name
        for name in listed.splitlines()
        # The plan is a history; this file names the patterns it looks for.
        if name not in {"docs/PLAN.md", "tests/platform/test_docs_index.py"}
        and (PROJECT_ROOT / name).is_file()
    ]


def test_references_to_root_readme_sections_name_sections_that_exist() -> None:
    headings: set[str] = set(
        MARKDOWN_HEADING.findall(README.read_text(encoding="utf-8"))
    )
    stale: list[str] = []
    pointers: list[str] = []
    for document in tracked_documents():
        text: str = document.read_text(encoding="utf-8")
        name: str = document.relative_to(PROJECT_ROOT).as_posix()
        stale.extend(
            f"{name}: {section}"
            for section in ROOT_README_SECTION.findall(text)
            if section not in headings
        )
        if ROOT_README_POINTER.search(text):
            pointers.append(name)

    # The README is a map now; link the docs/dev guide that holds the topic.
    assert stale == []
    assert pointers == []
