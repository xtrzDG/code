"""vulture finds no dead code in app/ and scripts/ ([tool.vulture]).

Delete code that nothing uses. Only a name that is used from outside Python
(a serialized response field, an enum value on the wire, a reserved setting)
goes into vulture_whitelist.py, in the section that explains why. The
whitelist is a ratchet: it holds at most WHITELISTED_NAMES names, one
statement `_.name` each, and the number comes down whenever a name leaves it.
The names are counted from the syntax tree, so a statement that whitelists
more than one name (`_.a, _.b`, `_.a(_.b)`, `_.a.b`) is refused, not counted
once.
"""

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
VULTURE: Path = Path(sys.executable).with_name("vulture")
WHITELIST: Path = PROJECT_ROOT / "vulture_whitelist.py"
WHITELISTED_NAMES: int = 506


@dataclass(frozen=True)
class WhitelistScan:
    names: tuple[str, ...]
    stray_lines: tuple[int, ...]


def _is_single_entry(statement: ast.stmt) -> bool:
    # Exactly `_.name`: an expression statement holding one attribute of `_`.
    if not isinstance(statement, ast.Expr):
        return False
    value: ast.expr = statement.value
    return (
        isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Name)
        and value.value.id == "_"
    )


def _is_header_end(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == "_"
    )


def scan_whitelist(source: str) -> WhitelistScan:
    statements: list[ast.stmt] = ast.parse(source).body
    header_end: int = next(
        index + 1
        for index, statement in enumerate(statements)
        if _is_header_end(statement)
    )
    names: list[str] = []
    stray_lines: list[int] = []
    for statement in statements[header_end:]:
        if _is_single_entry(statement):
            assert isinstance(statement, ast.Expr)
            assert isinstance(statement.value, ast.Attribute)
            names.append(statement.value.attr)
        else:
            stray_lines.append(statement.lineno)
    return WhitelistScan(names=tuple(names), stray_lines=tuple(stray_lines))


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
    names: int = len(scan_whitelist(WHITELIST.read_text(encoding="utf-8")).names)

    assert names <= WHITELISTED_NAMES, (
        f"vulture_whitelist.py lists {names} names, more than the "
        f"{WHITELISTED_NAMES} allowed. Delete the unused code instead; a name "
        "used only from outside Python replaces another entry that is gone."
    )
    assert names == WHITELISTED_NAMES, (
        f"vulture_whitelist.py lists {names} names: lower WHITELISTED_NAMES "
        f"in {Path(__file__).name} to {names} so the ratchet holds."
    )


def test_every_whitelist_statement_is_a_single_name() -> None:
    # A name hidden in another form (a tuple, a call) would escape the count.
    scan: WhitelistScan = scan_whitelist(WHITELIST.read_text(encoding="utf-8"))

    assert scan.stray_lines == ()


HEADER: str = "class _Whitelist: ...\n\n\n_ = _Whitelist()\n"


def test_the_scan_counts_one_name_per_statement() -> None:
    scan: WhitelistScan = scan_whitelist(
        HEADER + "# reason\n_.first  # a.py\n_.second  # b.py\n"
    )

    assert scan == WhitelistScan(names=("first", "second"), stray_lines=())


def test_the_scan_refuses_several_names_in_one_statement() -> None:
    scan: WhitelistScan = scan_whitelist(
        HEADER + "_.kept\n_.one, _.two\n_.three(_.four)\n_.five.six\n_.seven; _.eight\n"
    )

    assert scan.names == ("kept", "seven", "eight")
    assert scan.stray_lines == (6, 7, 8)
