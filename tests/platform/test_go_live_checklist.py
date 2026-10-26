"""
The owner's go-live checklist (docs/operations/go-live.md, summarised in
Russian in docs/LAUNCH.md, section 8) names only variables that exist where
the owner sets them, and every secret and variable the workflows read.

Every UPPER_SNAKE_CASE word of the checklist is a variable. Each one must be
read by something and listed where people look for it:

- read by the backend's settings (or a provider SDK): listed in .env.example;
- read by the cabinet: listed in web/.env.example;
- read by neither: a GitHub secret or variable of a workflow (`secrets.NAME`,
  `vars.NAME`), an option of a k6 scenario (`__ENV.NAME`) or a variable of
  the image's entrypoint (docker/entrypoint.sh).
"""

from dataclasses import dataclass

import pytest

from tests.platform.environment_sources import (
    LAUNCH_GUIDE,
    VARIABLE_NAME,
    backend_variables,
    cabinet_variables,
    entrypoint_variables,
    env_file_values,
    load_test_options,
    read,
    workflow_secrets,
    workflow_variables,
)

GO_LIVE_CHECKLIST: str = "docs/operations/go-live.md"
LAUNCH_SECTION_HEADING: str = "## 8. "
LAUNCH_SECTION: str = f"{LAUNCH_GUIDE}, section 8"
BACKEND_EXAMPLE: str = ".env.example"
CABINET_EXAMPLE: str = "web/.env.example"


@dataclass(frozen=True)
class Readers:
    """Who reads which variable, and where each is documented."""

    backend: frozenset[str]
    cabinet: frozenset[str]
    elsewhere: frozenset[str]
    backend_example: frozenset[str]
    cabinet_example: frozenset[str]

    @classmethod
    def of_repository(cls) -> Readers:
        return cls(
            backend=frozenset(backend_variables()),
            cabinet=frozenset(cabinet_variables()),
            elsewhere=frozenset(
                workflow_secrets()
                | workflow_variables()
                | load_test_options()
                | entrypoint_variables()
            ),
            backend_example=frozenset(env_file_values(BACKEND_EXAMPLE, False)),
            cabinet_example=frozenset(env_file_values(CABINET_EXAMPLE, True)),
        )

    def problems(self, name: str) -> list[str]:
        """Why the owner could not set `name` as the checklist says."""

        found: list[str] = []
        if name in self.backend and name not in self.backend_example:
            found.append(
                f"{name}: the backend's settings read it, "
                f"but {BACKEND_EXAMPLE} does not list it"
            )
        if name in self.cabinet and name not in self.cabinet_example:
            found.append(
                f"{name}: the cabinet reads it, but {CABINET_EXAMPLE} does not list it"
            )
        if name not in self.backend | self.cabinet | self.elsewhere:
            found.append(
                f"{name}: nothing reads it (not the backend's settings, the "
                "cabinet, a workflow's secrets./vars., a k6 scenario's __ENV. "
                "or docker/entrypoint.sh)"
            )
        return found


@pytest.fixture(scope="module")
def readers() -> Readers:
    return Readers.of_repository()


def launch_section() -> str:
    """docs/LAUNCH.md, section 8: the checklist in Russian."""

    guide: str = read(LAUNCH_GUIDE)
    start: int = guide.index(f"\n{LAUNCH_SECTION_HEADING}")
    end: int = guide.find("\n## ", start + 1)
    return guide[start:] if end == -1 else guide[start:end]


def checklist(document: str) -> str:
    return launch_section() if document == LAUNCH_SECTION else read(document)


@pytest.mark.parametrize("document", [GO_LIVE_CHECKLIST, LAUNCH_SECTION])
def test_every_variable_the_checklist_names_can_be_set(
    document: str, readers: Readers
) -> None:
    names: set[str] = set(VARIABLE_NAME.findall(checklist(document)))
    problems: list[str] = [
        problem for name in sorted(names) for problem in readers.problems(name)
    ]

    assert names, f"{document} names no variable at all"
    assert not problems, f"{document}:\n" + "\n".join(problems)


def test_the_checklist_names_every_secret_and_variable_of_the_workflows() -> None:
    named: set[str] = set(VARIABLE_NAME.findall(checklist(GO_LIVE_CHECKLIST)))
    unnamed: list[str] = sorted((workflow_secrets() | workflow_variables()) - named)

    assert not unnamed, (
        f"{GO_LIVE_CHECKLIST}, step 5, does not name what the workflows read: "
        + ", ".join(unnamed)
    )


def test_a_variable_nobody_reads_is_named_in_the_failure(readers: Readers) -> None:
    assert readers.problems("SENTRY_DSN") == []
    assert readers.problems("REPO_SETTINGS_TOKEN") == []
    assert readers.problems("WIDGET_VISITORS") == []
    [problem] = readers.problems("GO_LIVE_MADE_UP_KEY")
    assert problem.startswith("GO_LIVE_MADE_UP_KEY: nothing reads it")


def test_an_undocumented_backend_variable_is_named_in_the_failure() -> None:
    readers = Readers(
        backend=frozenset({"EMBEDDINGS_API_KEY"}),
        cabinet=frozenset({"SITE_URL"}),
        elsewhere=frozenset(),
        backend_example=frozenset(),
        cabinet_example=frozenset(),
    )

    assert readers.problems("EMBEDDINGS_API_KEY") == [
        "EMBEDDINGS_API_KEY: the backend's settings read it, "
        "but .env.example does not list it"
    ]
    assert readers.problems("SITE_URL") == [
        "SITE_URL: the cabinet reads it, but web/.env.example does not list it"
    ]


def test_the_launch_guide_points_to_the_checklist() -> None:
    assert GO_LIVE_CHECKLIST in launch_section()
