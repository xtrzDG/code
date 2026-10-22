"""vulture finds no dead code in app/ and scripts/ ([tool.vulture]).

Delete code that nothing uses. Only a name that is used from outside Python
(a serialized response field, an enum value on the wire, a reserved setting)
goes into vulture_whitelist.py, in the section that explains why. The
whitelist is a ratchet: it holds at most WHITELISTED_NAMES names, one per
line, and the number comes down whenever a name leaves it.
"""

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
VULTURE: Path = Path(sys.executable).with_name("vulture")
WHITELIST: Path = PROJECT_ROOT / "vulture_whitelist.py"
# One whitelisted name per line: `_.name  # where it is defined`.
WHITELIST_ENTRY: re.Pattern[str] = re.compile(r"^_\.\w+")
WHITELISTED_NAMES: int = 506


def test_no_dead_code() -> None:
    completed = subprocess.run(
        [str(VULTURE)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_the_whitelist_only_shrinks() -> None:
    lines: list[str] = WHITELIST.read_text(encoding="utf-8").splitlines()
    names: int = sum(1 for line in lines if WHITELIST_ENTRY.match(line))

    assert names <= WHITELISTED_NAMES, (
        f"vulture_whitelist.py lists {names} names, more than the "
        f"{WHITELISTED_NAMES} allowed. Delete the unused code instead; a name "
        "used only from outside Python replaces another entry that is gone."
    )
    assert names == WHITELISTED_NAMES, (
        f"vulture_whitelist.py lists {names} names: lower WHITELISTED_NAMES "
        f"in {Path(__file__).name} to {names} so the ratchet holds."
    )


def test_every_whitelist_line_is_an_entry_a_comment_or_the_header() -> None:
    # A name hidden in another form (a list, a call) would escape the count.
    lines: list[str] = WHITELIST.read_text(encoding="utf-8").splitlines()
    header_end: int = lines.index("_ = _Whitelist()") + 1
    stray: list[str] = [
        line
        for line in lines[header_end:]
        if line.strip()
        and not line.startswith("#")
        and WHITELIST_ENTRY.match(line) is None
    ]

    assert stray == []
