"""
Repositories never read a whole collection to find a few documents.

A `list_all()` (or the removed `_list()` of business-scoped repositories)
reads and validates every row of a table; on a busy platform that turns a
lookup into seconds and the 512 MB instance into an out-of-memory kill.
Repositories query by declared, indexed lookup fields instead
(`find_one_by_field`, `list_by_fields`, `count_by_fields`, `list_by_range`).

The allow-list below is for reads that must see every row by design. Do
not extend it for a lookup: declare a lookup field and index it.
"""

import ast
from pathlib import Path

REPOSITORIES_DIRECTORY: Path = Path(__file__).resolve().parents[2] / "app/repositories"
FULL_SCAN_METHOD_NAMES: frozenset[str] = frozenset({"list_all", "_list"})
ALLOWED_FULL_SCANS: dict[str, str] = {
    "business_repositories.py::BusinessRepository.list_all": (
        "the platform admin's client list and the periodic jobs that walk "
        "every business (trials, grace periods, usage, reminders, retention)"
    ),
}


def find_full_scans(module_path: Path) -> list[str]:
    """`file::Class.method` of every call of a full-scan method."""

    module: ast.Module = ast.parse(module_path.read_text(encoding="utf-8"))
    full_scans: list[str] = []
    for class_node in (node for node in module.body if isinstance(node, ast.ClassDef)):
        for method in class_node.body:
            if not isinstance(method, ast.FunctionDef):
                continue

            for node in ast.walk(method):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in FULL_SCAN_METHOD_NAMES
                ):
                    full_scans.append(
                        f"{module_path.name}::{class_node.name}.{method.name}"
                    )

    return full_scans


def test_repositories_query_by_index_instead_of_reading_whole_collections() -> None:
    full_scans: list[str] = [
        full_scan
        for module_path in sorted(REPOSITORIES_DIRECTORY.rglob("*.py"))
        for full_scan in find_full_scans(module_path)
    ]
    unexpected: list[str] = [
        full_scan for full_scan in full_scans if full_scan not in ALLOWED_FULL_SCANS
    ]

    assert unexpected == [], (
        "Repositories must not read whole collections (list_all / _list). "
        "Query by a declared lookup field instead "
        "(app/utilities/storage/document_lookup_fields.py and a migration). "
        f"Full scans found: {unexpected}"
    )


def test_the_allow_list_has_no_stale_entries() -> None:
    full_scans: set[str] = {
        full_scan
        for module_path in sorted(REPOSITORIES_DIRECTORY.rglob("*.py"))
        for full_scan in find_full_scans(module_path)
    }

    assert sorted(set(ALLOWED_FULL_SCANS) - full_scans) == []


def test_the_policy_catches_a_full_scan(tmp_path: Path) -> None:
    module_path = tmp_path / "sample_repositories.py"
    module_path.write_text(
        "class SampleRepository:\n"
        "    def find(self, value):\n"
        "        return [d for d in self._collection.list_all() if d.x == value]\n"
        "    def mine(self, business_id):\n"
        "        return self._list(business_id)\n",
        encoding="utf-8",
    )

    assert find_full_scans(module_path) == [
        "sample_repositories.py::SampleRepository.find",
        "sample_repositories.py::SampleRepository.mine",
    ]
