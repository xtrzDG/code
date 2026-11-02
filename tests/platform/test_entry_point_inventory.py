"""
The entry-point inventory (`docs/security/entry-points.json`) and the
permission matrix (`docs/security/permission-matrix.md`) are what
`scripts/entry_point_inventory.py` generates from the code today: a route,
job or command added without regenerating them fails here. The inventory
agrees with the reviewed tables the authorization tests prove, every
webhook names its signature, and every cabinet route handler is classified.
"""

import re
from collections import Counter
from pathlib import Path

import pytest

from scripts import entry_point_inventory
from scripts.entry_point_inventory import (
    REGENERATE,
    Inventory,
    generated_files,
    main,
    read_inventory,
    stale_files,
)
from scripts.entry_points.access_classes import (
    ACCESS_CLASSES,
    CUSTOMER,
    OWNER,
    PUBLIC,
    SIGNED_WEBHOOK,
)
from scripts.entry_points.api_routes import BRAND_PREFIX, BUSINESS_PREFIX, is_under
from scripts.entry_points.cabinet_routes import (
    CABINET_ROUTES,
    UnclassifiedRouteError,
    cabinet_entry_points,
    route_path,
)
from tests.platform.authorization_tables import OWNER_ONLY_OPERATIONS
from tests.platform.brand_matrix_checks import BRAND_OWNER_ONLY
from tests.platform.route_access_tables import PUBLIC_OPERATIONS, UNDOCUMENTED_ROUTES

ROOT: Path = Path(__file__).resolve().parents[2]
OPEN_CLASSES: frozenset[str] = frozenset({PUBLIC, SIGNED_WEBHOOK, CUSTOMER})
SIGNATURE_WORDS: tuple[str, ...] = ("signature", "secret", "token", "handshake")
PATH_PATTERN: re.Pattern[str] = re.compile(r"`((?:[\w.-]+/)+[\w.-]*)`")
# Today's numbers; fewer means entry points were lost to the inventory.
MINIMUM_API_OPERATIONS: int = 400
MINIMUM_PERIODIC_JOBS: int = 40
MINIMUM_QUEUED_JOBS: int = 20


@pytest.fixture(scope="module")
def inventory() -> Inventory:
    return read_inventory()


def test_the_inventory_and_the_matrix_are_generated_from_todays_code(
    inventory: Inventory,
) -> None:
    stale = stale_files(generated_files(inventory), write=False)

    assert stale == [], f"Run: {REGENERATE}"


def test_every_api_operation_is_listed_once_with_a_known_class(
    inventory: Inventory,
) -> None:
    keys = Counter(entry.key for entry in inventory.api)

    assert len(keys) >= MINIMUM_API_OPERATIONS
    assert [key for key, count in keys.items() if count > 1] == []
    assert {entry.access for entry in inventory.api} <= set(ACCESS_CLASSES)
    assert {entry.access for entry in inventory.cabinet} <= set(ACCESS_CLASSES)


def test_the_open_operations_are_exactly_the_reviewed_ones(
    inventory: Inventory,
) -> None:
    opened = {
        entry.key
        for entry in inventory.api
        if entry.access in OPEN_CLASSES
        and entry.method != "OPTIONS"
        and entry.path not in UNDOCUMENTED_ROUTES
    }

    assert opened == set(PUBLIC_OPERATIONS)


def test_the_owners_operations_are_those_the_matrices_prove(
    inventory: Inventory,
) -> None:
    owners = {entry.key for entry in inventory.api if entry.access == OWNER}

    business = {key for key in owners if is_under(key.split()[1], BUSINESS_PREFIX)}
    brand = {key for key in owners if is_under(key.split()[1], BRAND_PREFIX)}
    assert business == set(OWNER_ONLY_OPERATIONS)
    assert brand == set(BRAND_OWNER_ONLY)


def test_every_webhook_names_what_proves_its_sender(inventory: Inventory) -> None:
    webhooks = [entry for entry in inventory.api if entry.access == SIGNED_WEBHOOK]

    assert len(webhooks) >= 10
    assert [
        entry.key
        for entry in webhooks
        if not any(word in entry.protected_by.lower() for word in SIGNATURE_WORDS)
    ] == []


def test_only_the_reviewed_routes_are_kept_out_of_production(
    inventory: Inventory,
) -> None:
    hidden = {entry.path for entry in inventory.api if not entry.in_production}

    assert hidden == {
        "/docs",
        "/docs/oauth2-redirect",
        "/openapi.json",
        "/redoc",
        "/widget/demo",
    }


def test_every_classified_cabinet_route_still_exists(inventory: Inventory) -> None:
    assert {entry.path for entry in inventory.cabinet} == set(CABINET_ROUTES)


def test_a_new_cabinet_route_must_be_classified(tmp_path: Path) -> None:
    handler = tmp_path / "(site)" / "api" / "new" / "route.ts"
    handler.parent.mkdir(parents=True)
    handler.write_text("export async function POST() {}\n", encoding="utf-8")

    assert route_path(handler, tmp_path) == "/api/new"
    with pytest.raises(UnclassifiedRouteError, match="/api/new"):
        cabinet_entry_points(tmp_path)


def test_the_jobs_and_the_commands_are_listed(inventory: Inventory) -> None:
    periodic = [str(job["name"]) for job in inventory.periodic_jobs]
    queued = [str(job["name"]) for job in inventory.queued_jobs]
    commands = {str(item["name"]): item for item in inventory.commands}

    assert len(periodic) >= MINIMUM_PERIODIC_JOBS
    assert len(set(periodic)) == len(periodic)
    assert len(queued) >= MINIMUM_QUEUED_JOBS
    assert {"purge_expired_personal_data", "verify_audit_chain"} <= set(periodic)
    assert {"workshop api", "workshop worker", "workshop backup"} <= set(commands)
    assert commands["workshop backup"]["run_by_render"] == [
        "workshop-backup (cron, 17 1 * * *)"
    ]
    for item in commands.values():
        module = ROOT.joinpath(*str(item["module"]).split(".")).with_suffix(".py")
        assert module.is_file(), item


def test_the_matrix_names_only_paths_that_exist() -> None:
    text = (ROOT / "docs" / "security" / "permission-matrix.md").read_text("utf-8")
    paths = set(PATH_PATTERN.findall(text))

    assert len(paths) > 15
    assert sorted(path for path in paths if not (ROOT / path).exists()) == []


def test_check_mode_reports_a_stale_file_and_writing_renews_it(
    inventory: Inventory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(entry_point_inventory, "read_inventory", lambda: inventory)
    monkeypatch.setattr(entry_point_inventory, "ROOT", tmp_path)
    for name in ("INVENTORY_PATH", "MATRIX_PATH"):
        target = tmp_path / f"{name}.txt"
        target.write_text("stale\n", encoding="utf-8")
        monkeypatch.setattr(entry_point_inventory, name, target)

    assert main(["--check"]) == 1
    assert (tmp_path / "INVENTORY_PATH.txt").read_text("utf-8") == "stale\n"
    assert main([]) == 0
    assert main(["--check"]) == 0
