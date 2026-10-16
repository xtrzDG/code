"""vulture finds no dead code in app/ and scripts/ ([tool.vulture]).

Delete code that nothing uses. Only a name that is used from outside Python
(a serialized response field, an enum value on the wire, a reserved setting)
goes into vulture_whitelist.py, in the section that explains why.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
VULTURE: Path = Path(sys.executable).with_name("vulture")


def test_no_dead_code() -> None:
    completed = subprocess.run(
        [str(VULTURE)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
