"""
The secrets inventory (docs/security/secrets-inventory.md) lists every
secret the code reads: the backend's settings and SDKs, the cabinet's
server, the workflows' secrets. Each row names its purpose, owner, store,
rotation period (at most a year) and procedure, and names a variable that
still exists.
"""

import re

from tests.legal.governance_documents import (
    OPERATIONS,
    missing_paths,
    read,
    table_rows,
)
from tests.platform.deployment_variables import DEPLOYMENT_VARIABLES
from tests.platform.environment_sources import (
    backend_variables,
    cabinet_variables,
    workflow_secrets,
)

INVENTORY: str = "docs/security/secrets-inventory.md"
# Variable names that hold a secret: secrets, tokens, passwords, every key
# but a public one (`*_PUBLIC_KEY`, Turnstile's `*_SITE_KEY`), connection
# strings with their password, the backups' private identity, a DSN.
SECRET_NAME: re.Pattern[str] = re.compile(
    r"(SECRET|TOKEN|PASSWORD|(?<!PUBLIC)(?<!SITE)_KEYS?|DATABASE_URL(?:_[A-Z]+)?"
    r"|OTLP_HEADERS|IDENTITY|DSN)$"
)
VARIABLE: re.Pattern[str] = re.compile(r"`([A-Z][A-Z0-9_]*)`")
SECRET_COLUMNS: int = 6
ROTATION: re.Pattern[str] = re.compile(r"(\d+) months|on exposure|with its role")
LONGEST_ROTATION_MONTHS: int = 12


def code_secrets() -> set[str]:
    read_by_code = backend_variables() | workflow_secrets() | cabinet_variables()
    return {name for name in read_by_code if SECRET_NAME.search(name)}


def secret_rows() -> list[list[str]]:
    """The rows of the inventory's six-column tables (one per secret)."""

    return [row for row in table_rows(read(INVENTORY)) if len(row) == SECRET_COLUMNS]


def listed_secrets() -> set[str]:
    return {name for row in secret_rows() for name in VARIABLE.findall(row[0])}


def test_every_secret_the_code_reads_is_in_the_inventory() -> None:
    secrets = code_secrets()

    assert len(secrets) > 40
    assert sorted(secrets - listed_secrets()) == [], f"Add these secrets to {INVENTORY}"


def test_every_listed_secret_is_still_read_somewhere() -> None:
    known = (
        backend_variables()
        | workflow_secrets()
        | cabinet_variables()
        | set(DEPLOYMENT_VARIABLES)
    )

    assert sorted(listed_secrets() - known) == []


def test_every_secret_names_purpose_owner_store_rotation_and_procedure() -> None:
    rows = secret_rows()

    assert len(rows) > 30
    for row in rows:
        assert all(cell for cell in row), row
        rotation = ROTATION.search(row[4])
        assert rotation is not None, row
        if rotation.group(1) is not None:
            assert int(rotation.group(1)) <= LONGEST_ROTATION_MONTHS, row


def test_the_inventory_names_only_paths_that_exist() -> None:
    assert missing_paths(read(INVENTORY), OPERATIONS) == []
