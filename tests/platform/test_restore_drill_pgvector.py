"""
Once pgvector is enabled in production (migration 1211, docs/LAUNCH.md),
every backup holds the vector extension and a vector column: both restore
drills restore into a server that offers pgvector, the nightly drill backs
up a database with the embeddings enabled, and the runbook says a recovery
server needs the extension.
"""

from pathlib import Path
from typing import Any, cast

import yaml

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
RESTORE_DRILL: Path = PROJECT_ROOT / ".github" / "workflows" / "restore-drill.yml"
RUNBOOK: Path = PROJECT_ROOT / "docs" / "operations" / "backup-restore.md"


def jobs() -> dict[str, dict[str, Any]]:
    workflow = cast(
        dict[str, Any], yaml.safe_load(RESTORE_DRILL.read_text(encoding="utf-8"))
    )
    return cast(dict[str, dict[str, Any]], workflow["jobs"])


def test_both_drills_restore_into_postgres_with_pgvector() -> None:
    images: dict[str, str] = {
        name: str(job["services"]["postgres"]["image"]) for name, job in jobs().items()
    }

    assert images.keys() == {"round-trip", "production"}
    assert all(image.startswith("pgvector/pgvector:") for image in images.values())
    assert all(image.endswith("-pg16") for image in images.values())


def test_the_nightly_drill_backs_up_a_database_with_the_embeddings_enabled() -> None:
    steps: list[dict[str, Any]] = jobs()["round-trip"]["steps"]
    names: list[str] = [str(step.get("name", "")) for step in steps]
    enable: int = names.index("Knowledge embeddings enabled, as in production")

    assert names.index("Migrate and seed realistic rows") < enable
    assert enable < names.index("workshop backup")
    script: str = str(steps[enable]["run"])
    assert "create extension if not exists vector;" in script
    assert "select workshop.enable_knowledge_embeddings();" in script


def test_the_runbook_asks_for_pgvector_on_the_recovery_server() -> None:
    runbook: str = RUNBOOK.read_text(encoding="utf-8")

    assert "pgvector/pgvector:0.8.0-pg16" in runbook
    assert "`create extension vector;` in `template1`" in runbook
