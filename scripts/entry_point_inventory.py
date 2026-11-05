"""
Write the entry-point inventory: every HTTP route of the API and of the
cabinet, every webhook, worker job and command of the backend image with
its access class (public, signed webhook, customer, account, staff, owner,
platform admin, API key, ...), and the permission matrix by role:

    uv run python -m scripts.entry_point_inventory

It writes `docs/security/entry-points.json` and
`docs/security/permission-matrix.md`. With `--check` nothing is written;
the exit status is 1 when either file is out of date
(`tests/platform/test_entry_point_inventory.py` runs the same comparison,
so a route added without regenerating them fails CI). Read from the live
application and the reviewed tables of the authorization tests
(`scripts/entry_points/api_routes.py`).
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from app.containers.app import AppContainer
from app.main import build_application
from scripts.entry_points.access_classes import ACCESS_CLASSES, HttpEntryPoint
from scripts.entry_points.api_routes import api_entry_points
from scripts.entry_points.background import commands, periodic_jobs, queued_jobs
from scripts.entry_points.cabinet_routes import cabinet_entry_points
from scripts.entry_points.permission_matrix import render_permission_matrix

ROOT: Path = Path(__file__).resolve().parents[1]
INVENTORY_PATH: Path = ROOT / "docs" / "security" / "entry-points.json"
MATRIX_PATH: Path = ROOT / "docs" / "security" / "permission-matrix.md"
REGENERATE: str = "uv run python -m scripts.entry_point_inventory"


@dataclass(frozen=True)
class Inventory:
    """Every entry point, read once from the code."""

    api: list[HttpEntryPoint]
    cabinet: list[HttpEntryPoint]
    periodic_jobs: list[dict[str, object]]
    queued_jobs: list[dict[str, object]]
    commands: list[dict[str, object]]


def read_inventory() -> Inventory:
    container: AppContainer = AppContainer()
    return Inventory(
        api=api_entry_points(build_application(container)),
        cabinet=cabinet_entry_points(),
        periodic_jobs=periodic_jobs(container),
        queued_jobs=queued_jobs(container),
        commands=commands(),
    )


def entry_lines(entries: list[dict[str, object]]) -> str:
    """A JSON list with one entry per line, so a diff shows one route per line."""

    if not entries:
        return "[]"
    lines: list[str] = [json.dumps(entry, ensure_ascii=False) for entry in entries]
    return "[\n    " + ",\n    ".join(lines) + "\n  ]"


def render_inventory(inventory: Inventory) -> str:
    """The JSON document, ending with a newline."""

    head: dict[str, object] = {
        "generated_by": REGENERATE,
        "checked_by": "tests/platform/test_entry_point_inventory.py",
        "access_classes": ACCESS_CLASSES,
    }
    parts: dict[str, str] = {
        key: json.dumps(value, ensure_ascii=False, indent=2).replace("\n", "\n  ")
        for key, value in head.items()
    }
    parts["api"] = entry_lines([entry.as_json() for entry in inventory.api])
    parts["cabinet"] = entry_lines([entry.as_json() for entry in inventory.cabinet])
    parts["periodic_jobs"] = entry_lines(inventory.periodic_jobs)
    parts["queued_jobs"] = entry_lines(inventory.queued_jobs)
    parts["commands"] = entry_lines(inventory.commands)
    body: str = ",\n".join(
        f"  {json.dumps(key)}: {text}" for key, text in parts.items()
    )
    return "{\n" + body + "\n}\n"


def generated_files(inventory: Inventory) -> dict[Path, str]:
    return {
        INVENTORY_PATH: render_inventory(inventory),
        MATRIX_PATH: render_permission_matrix(inventory.api, inventory.cabinet),
    }


def stale_files(files: dict[Path, str], write: bool) -> list[Path]:
    """The files whose text differs from `files`; rewritten when `write`."""

    stale: list[Path] = []
    for path, text in files.items():
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            continue
        stale.append(path)
        if write:
            path.write_text(text, encoding="utf-8")
    return stale


def main(arguments: list[str]) -> int:
    is_check: bool = "--check" in arguments
    stale: list[Path] = stale_files(
        generated_files(read_inventory()), write=not is_check
    )
    for path in stale:
        verb: str = "is out of date" if is_check else "written"
        sys.stdout.write(f"{path.relative_to(ROOT)} {verb}\n")
    if is_check and stale:
        sys.stdout.write(f"Run: {REGENERATE}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
