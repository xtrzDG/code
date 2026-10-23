"""
The composition root's `# type: ignore` comments only ever go down.

dependency-injector types a child container edge as the provider it is,
not as the container it stands for, so every edge of app/containers needs
a local `# type: ignore[assignment]` (app/containers/AGENTS.md). Those
comments are the one untyped part of the backend. This ratchet keeps their
number from growing: a new context is wired as a typed root in plain
Python (ADR 0010, the pilot is app/containers/feedback/), and when a
context leaves the provider graph, CONTAINER_TYPE_IGNORES comes down.
"""

import ast
import io
import tokenize
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
CONTAINERS: Path = PROJECT_ROOT / "app" / "containers"
CONTAINER_TYPE_IGNORES: int = 1090
# Typed composition roots: plain Python, no provider graph, nothing silenced.
TYPED_ROOTS: tuple[Path, ...] = (
    CONTAINERS / "feedback",
    CONTAINERS / "passkeys",
    CONTAINERS / "payments",
    CONTAINERS / "adapters" / "provider_resilience.py",
    CONTAINERS / "role_chain_factories.py",
)
ALLOWED_IGNORE: str = "# type: ignore[assignment]"


def type_ignore_comments(path: Path) -> list[str]:
    """The `type: ignore` comments of a file (docstrings and strings excluded)."""

    source: str = path.read_text(encoding="utf-8")
    return [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT and "type: ignore" in token.string
    ]


def container_sources() -> list[Path]:
    return sorted(CONTAINERS.rglob("*.py"))


def typed_root_sources() -> list[Path]:
    return sorted(
        path
        for root in TYPED_ROOTS
        for path in ([root] if root.is_file() else root.rglob("*.py"))
    )


def test_the_number_of_container_ignores_only_goes_down() -> None:
    count: int = sum(len(type_ignore_comments(path)) for path in container_sources())

    assert count <= CONTAINER_TYPE_IGNORES, (
        f"app/containers has {count} `# type: ignore` comments, more than the "
        f"{CONTAINER_TYPE_IGNORES} allowed. Wire the new context as a typed "
        "root (docs/adr/0010-composition-root.md) instead of adding edges."
    )
    assert count == CONTAINER_TYPE_IGNORES, (
        f"app/containers has {count} `# type: ignore` comments: lower "
        f"CONTAINER_TYPE_IGNORES to {count} so the ratchet holds."
    )


def test_every_container_ignore_is_the_documented_edge_kind() -> None:
    # Only the edge mismatch of dependency-injector is silenced, never a
    # real type error behind a bare or broader ignore.
    others: list[str] = [
        f"{path.relative_to(PROJECT_ROOT)}: {comment}"
        for path in container_sources()
        for comment in type_ignore_comments(path)
        if comment.strip() != ALLOWED_IGNORE
    ]

    assert others == []


def test_typed_roots_are_plain_python_without_ignores() -> None:
    sources: list[Path] = typed_root_sources()
    silenced: list[str] = [
        str(path.relative_to(PROJECT_ROOT))
        for path in sources
        if type_ignore_comments(path)
    ]
    on_the_provider_graph: list[str] = [
        str(path.relative_to(PROJECT_ROOT))
        for path in sources
        if any(
            isinstance(node, ast.ImportFrom | ast.Import)
            and any(
                name.startswith("dependency_injector")
                for name in (
                    [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else [alias.name for alias in node.names]
                )
            )
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        )
    ]

    assert len(sources) >= 5
    assert silenced == []
    assert on_the_provider_graph == []
