"""Which Dependabot pull requests merge themselves after a green CI."""

import io

import pytest

from scripts.dependabot_automerge import (
    EXIT_LEAVE,
    EXIT_MERGE,
    main,
    reason_to_leave,
    updated_dependencies,
)

GROUPED_MINOR = """Bump the vitest group in /web with 2 updates

Bumps the vitest group in /web with 2 updates: vitest and @vitest/coverage-v8.

---
updated-dependencies:
- dependency-name: vitest
  dependency-version: 5.1.0
  dependency-type: direct:development
  update-type: version-update:semver-minor
  dependency-group: vitest
- dependency-name: "@vitest/coverage-v8"
  dependency-version: 5.0.4
  dependency-type: direct:development
  update-type: version-update:semver-patch
  dependency-group: vitest
...

Signed-off-by: dependabot[bot] <support@github.com>
"""


def with_entry(update_type: str, group_line: str) -> str:
    return (
        "Bump next from 16.0.1 to 17.0.0 in /web\n\n---\n"
        "updated-dependencies:\n"
        "- dependency-name: next\n"
        "  dependency-version: 17.0.0\n"
        "  dependency-type: direct:production\n"
        f"  update-type: {update_type}\n"
        f"{group_line}"
        "...\n"
    )


def test_the_front_matter_names_every_update_with_its_type_and_group() -> None:
    dependencies = updated_dependencies(GROUPED_MINOR)

    assert [(item.name, item.update_type, item.group) for item in dependencies] == [
        ("vitest", "version-update:semver-minor", "vitest"),
        ("@vitest/coverage-v8", "version-update:semver-patch", "vitest"),
    ]
    assert reason_to_leave(dependencies) is None


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        (
            with_entry("version-update:semver-major", "  dependency-group: nextjs\n"),
            "next is a version-update:semver-major",
        ),
        (
            with_entry("version-update:semver-patch", ""),
            "next is not part of a group",
        ),
        (
            with_entry("", "  dependency-group: nextjs\n"),
            "next is a no update type",
        ),
        ("Bump next by hand\n\nNo metadata here.\n", "no Dependabot metadata"),
        ("---\nsomething-else: 1\n...\n", "no Dependabot metadata"),
    ],
)
def test_anything_but_a_grouped_patch_or_minor_waits_for_a_person(
    message: str, reason: str
) -> None:
    found = reason_to_leave(updated_dependencies(message))

    assert found is not None
    assert found.startswith(reason)


def test_one_major_in_a_group_keeps_the_whole_group_waiting() -> None:
    message = GROUPED_MINOR.replace(
        "update-type: version-update:semver-patch",
        "update-type: version-update:semver-major",
    )

    assert reason_to_leave(updated_dependencies(message)) == (
        "@vitest/coverage-v8 is a version-update:semver-major"
    )


def test_main_answers_with_its_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(GROUPED_MINOR))
    assert main() == EXIT_MERGE
    assert "vitest, @vitest/coverage-v8" in capsys.readouterr().out

    monkeypatch.setattr(
        "sys.stdin", io.StringIO(with_entry("version-update:semver-major", ""))
    )
    assert main() == EXIT_LEAVE
    assert capsys.readouterr().out.startswith("Left for review: next")
