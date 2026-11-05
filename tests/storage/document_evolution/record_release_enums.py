"""
Record the enum values of the last release (tests/storage/release_enums.json).

    uv run python -m tests.storage.document_evolution.record_release_enums \
        <commit> <release name>

Run it when a release reaches production, with the commit `release` points
at (`git rev-parse origin/release`) and a name for it. From then on a stored
enum value that release lacks must sit behind a closed release gate
(docs/operations/deploys.md, "Enum values one release ahead").
"""

import json
import sys

from tests.storage.document_evolution.enum_snapshot import (
    SNAPSHOT_PATH,
    enums_at,
    git,
)

USAGE: str = "usage: record_release_enums <commit> <release name>"


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(USAGE, file=sys.stderr)
        return 2

    commit: str = git("rev-parse", "--verify", f"{arguments[0]}^{{commit}}").strip()
    snapshot: dict[str, object] = {
        "release": arguments[1],
        "commit": commit,
        "documents": enums_at(commit),
    }
    SNAPSHOT_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{SNAPSHOT_PATH.name}: {arguments[1]} at {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
