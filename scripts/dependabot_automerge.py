"""
Whether a Dependabot pull request may merge itself once CI is green
(.github/workflows/automerge.yml):

    gh api "repos/OWNER/REPO/commits/SHA" --jq .commit.message \\
        | uv run --no-project python -m scripts.dependabot_automerge

Reads the head commit's message from stdin. Dependabot ends it with YAML
front matter that names every updated dependency, its update type and its
group (.github/dependabot.yml). Exit code 0 (merge) only when there is at
least one update and every one belongs to a group and is a patch or a
minor; 1 (leave it for a person) otherwise, with the reason printed. Majors,
single updates and security fixes outside a group always wait.
"""

import sys
from dataclasses import dataclass

EXIT_MERGE: int = 0
EXIT_LEAVE: int = 1
METADATA_START: str = "updated-dependencies:"
MERGEABLE_UPDATE_TYPES: frozenset[str] = frozenset(
    {"version-update:semver-patch", "version-update:semver-minor"}
)


@dataclass(frozen=True)
class UpdatedDependency:
    """One entry of Dependabot's `updated-dependencies` front matter."""

    name: str
    update_type: str
    group: str


def unquote(value: str) -> str:
    text: str = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]

    return text


def front_matter(message: str) -> list[str]:
    lines: list[str] = message.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip() == "---" and lines[index + 1].strip() == METADATA_START:
            body: list[str] = []
            for item in lines[index + 2 :]:
                if item.strip() in {"...", "---"}:
                    break
                body.append(item)
            return body

    return []


def updated_dependencies(message: str) -> list[UpdatedDependency]:
    entries: list[dict[str, str]] = []
    for line in front_matter(message):
        stripped: str = line.strip()
        if stripped.startswith("- "):
            entries.append({})
            stripped = stripped[2:]
        if not entries or ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        entries[-1][key.strip()] = unquote(value)
    return [
        UpdatedDependency(
            name=entry.get("dependency-name", ""),
            update_type=entry.get("update-type", ""),
            group=entry.get("dependency-group", ""),
        )
        for entry in entries
    ]


def reason_to_leave(dependencies: list[UpdatedDependency]) -> str | None:
    if not dependencies:
        return "no Dependabot metadata in the head commit"

    for dependency in dependencies:
        if not dependency.group:
            return f"{dependency.name or 'an update'} is not part of a group"
        if dependency.update_type not in MERGEABLE_UPDATE_TYPES:
            kind: str = dependency.update_type or "no update type"
            return f"{dependency.name} is a {kind}"

    return None


def main() -> int:
    dependencies: list[UpdatedDependency] = updated_dependencies(sys.stdin.read())
    reason: str | None = reason_to_leave(dependencies)
    if reason is not None:
        print(f"Left for review: {reason}.")
        return EXIT_LEAVE

    names: str = ", ".join(dependency.name for dependency in dependencies)
    print(f"Merging the group's patch and minor updates: {names}.")
    return EXIT_MERGE


if __name__ == "__main__":
    raise SystemExit(main())
