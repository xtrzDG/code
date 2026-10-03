"""The role layers of `.importlinter` hold (gateways > ... > schemas), and the
use-case packages are independent of each other (shared code lives in
`app.use_cases.shared`).

A broken contract is fixed by moving code to the role it belongs to (see
docs/adr/0002-role-chain-and-layers.md), never with ignore_imports.
"""

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
LINT_IMPORTS: Path = Path(sys.executable).with_name("lint-imports")
CONFIGURATION: Path = PROJECT_ROOT / ".importlinter"


def test_import_contracts_are_kept() -> None:
    completed = subprocess.run(
        [str(LINT_IMPORTS), "--config", str(CONFIGURATION), "--no-cache"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_contracts_have_no_ignored_imports() -> None:
    configuration_text: str = CONFIGURATION.read_text(encoding="utf-8")

    assert (
        re.search(r"^\s*ignore_imports\s*=", configuration_text, re.MULTILINE) is None
    )
    assert "type = layers" in configuration_text


def test_every_use_case_package_is_independent() -> None:
    """A new use-case package joins the independence contract (all but shared)."""

    configuration_text: str = CONFIGURATION.read_text(encoding="utf-8")
    contract_text: str = configuration_text.split(
        "[importlinter:contract:use-case-packages]", maxsplit=1
    )[1]
    listed: set[str] = set(
        re.findall(r"^\s+app\.use_cases\.([a-z_]+)$", contract_text, re.MULTILINE)
    )
    packages: set[str] = {
        path.name
        for path in (PROJECT_ROOT / "app" / "use_cases").iterdir()
        if (path / "__init__.py").is_file() and path.name != "shared"
    }

    assert "type = independence" in contract_text
    assert listed == packages
