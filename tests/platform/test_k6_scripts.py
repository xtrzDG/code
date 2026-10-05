"""
The k6 load scenarios import their shared helpers from files that are in
the repository: a checkout (CI's) without them fails the weekly load run
before it starts, as an ignored `lib/` folder once did.
"""

import re
from pathlib import Path

K6_FOLDER: Path = Path(__file__).resolve().parents[2] / "perf" / "k6"
RELATIVE_IMPORT = re.compile(
    r"""^\s*import\s[^;]*?from\s+["'](\.{1,2}/[^"']+)["']""", re.M
)


def relative_imports(script: Path) -> list[str]:
    return RELATIVE_IMPORT.findall(script.read_text())


def test_every_scenario_finds_the_helpers_it_imports() -> None:
    scenarios = sorted(K6_FOLDER.glob("*.js"))
    missing = [
        f"{script.name}: {target}"
        for script in scenarios
        for target in relative_imports(script)
        if not (script.parent / target).is_file()
    ]

    assert scenarios, "no k6 scenarios found in perf/k6"
    assert missing == []


def test_the_helpers_export_what_the_scenarios_import() -> None:
    helpers = (K6_FOLDER / "lib" / "manifest.js").read_text()
    exported = set(re.findall(r"^export (?:const|function) (\w+)", helpers, re.M))
    imported = {
        name.strip()
        for script in K6_FOLDER.glob("*.js")
        for names in re.findall(
            r"""import\s*\{([^}]*)\}\s*from\s*["']\./lib/manifest\.js["']""",
            script.read_text(),
        )
        for name in names.split(",")
    }

    assert imported <= exported, sorted(imported - exported)
