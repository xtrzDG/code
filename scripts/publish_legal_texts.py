"""
Record the fingerprints of the published legal texts (docs/legal) in
docs/legal/published.json, so a text owners accepted or read is never
edited in place; tests/legal fails when one changes:

    uv run python -m scripts.publish_legal_texts

A new file (a new dated version) is added; a changed one is refused, since
the change belongs in a new version with a new date (and, for the DPA, a
new DPA_DOCUMENT_VERSION that owners accept again). `--check` writes
nothing and exits 1 when anything differs.
"""

import json
import sys
from pathlib import Path

from app.registries.legal.legal_document_registry import (
    DEFAULT_LEGAL_DOCUMENTS_DIRECTORY,
)
from app.utilities.legal.legal_text_fingerprints import LEGAL_TEXT_NAME, fingerprint

MANIFEST_NAME: str = "published.json"


def published_texts(directory: Path) -> dict[str, str]:
    """Every legal text of the directory and its fingerprint, by file name."""

    return {
        path.name: fingerprint(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.md"))
        if LEGAL_TEXT_NAME.match(path.name) is not None
    }


def read_manifest(directory: Path) -> dict[str, str]:
    path: Path = directory / MANIFEST_NAME
    if not path.exists():
        return {}

    recorded: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return recorded


def differences(directory: Path) -> tuple[list[str], list[str], list[str]]:
    """(changed, new, missing) file names against the manifest."""

    current: dict[str, str] = published_texts(directory)
    recorded: dict[str, str] = read_manifest(directory)
    changed: list[str] = sorted(
        name for name in current if name in recorded and recorded[name] != current[name]
    )
    new: list[str] = sorted(name for name in current if name not in recorded)
    missing: list[str] = sorted(name for name in recorded if name not in current)
    return changed, new, missing


def main(
    arguments: list[str], directory: Path = DEFAULT_LEGAL_DOCUMENTS_DIRECTORY
) -> int:
    changed, new, missing = differences(directory)
    for name in changed:
        sys.stdout.write(
            f"{name}: changed after it was published; put the change in a new "
            "dated version instead\n"
        )
    for name in missing:
        sys.stdout.write(f"{name}: published, but the file is gone\n")
    if "--check" in arguments:
        for name in new:
            sys.stdout.write(f"{name}: not recorded yet\n")
        return 1 if changed or new or missing else 0

    if changed or missing:
        return 1

    manifest: dict[str, str] = read_manifest(directory) | {
        name: value for name, value in published_texts(directory).items() if name in new
    }
    (directory / MANIFEST_NAME).write_text(
        json.dumps(dict(sorted(manifest.items())), indent=2) + "\n", encoding="utf-8"
    )
    for name in new:
        sys.stdout.write(f"{name}: recorded\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
