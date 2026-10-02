"""The role layers of `.importlinter` hold (gateways > ... > schemas).

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
