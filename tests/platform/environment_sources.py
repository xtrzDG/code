"""Where environment variables are read and declared: code, examples, docs.

Sources of truth:

- the settings assembler (`app/utilities/config_helpers/app_settings/`) and
  the provider SDKs for the backend; `.env.example` and the "Окружение"
  table of `README.md` for people;
- `web/src` (the cabinet's server code) for the cabinet; `web/.env.example`
  and the "Environment" table of `web/README.md` for people;
- `docker-compose.yml` and `render.yaml` for the deployments.

The owner's launch guide (`docs/LAUNCH.md`) may name only variables, API
routes and files that exist.
"""

import ast
import re
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]

# The assembler and its sections, one module per topic.
ASSEMBLER_DIRECTORY: Path = (
    ROOT / "app" / "utilities" / "config_helpers" / "app_settings"
)
VARIABLE_NAME: re.Pattern[str] = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+")
LAUNCH_GUIDE: str = "docs/LAUNCH.md"

# Read by the provider SDKs themselves: the clients never pass the key, so
# the SDK takes it from the environment. Set like any other variable.
SDK_VARIABLES: frozenset[str] = frozenset({"OPENAI_API_KEY", "ANTHROPIC_API_KEY"})

# Set by Next.js itself (`next build`, `next start`), never by people.
NEXT_JS_VARIABLES: frozenset[str] = frozenset({"NODE_ENV", "NEXT_RUNTIME"})


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def assembler_variables() -> set[str]:
    """Every variable name written in the settings assembler."""

    return {
        node.value
        for module_path in sorted(ASSEMBLER_DIRECTORY.glob("*.py"))
        for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and VARIABLE_NAME.fullmatch(node.value) is not None
    }


def backend_variables() -> set[str]:
    """What the backend reads: the assembler and the SDKs."""

    return assembler_variables() | SDK_VARIABLES


def env_file_values(relative_path: str, include_commented: bool) -> dict[str, str]:
    """`NAME=value` lines of an env file (and `# NAME=value` when asked)."""

    prefix: str = r"^(?:#\s*)?" if include_commented else r"^"
    pattern: str = prefix + r"([A-Z][A-Z0-9_]*)=(.*)$"
    return dict(re.findall(pattern, read(relative_path), re.MULTILINE))


def table_variables(relative_path: str, heading: str) -> set[str]:
    """Variables named in the first column of the tables under a heading."""

    lines: list[str] = read(relative_path).splitlines()
    level: int = len(heading.split(" ", 1)[0])
    names: set[str] = set()
    is_in_code: bool = False
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("```"):
            is_in_code = not is_in_code
        heading_match = re.match(r"(#+) ", line)
        if (
            not is_in_code
            and heading_match is not None
            and len(heading_match.group(1)) <= level
        ):
            break

        cells: list[str] = line.split("|")
        if line.startswith("|") and len(cells) > 2:
            names.update(re.findall(r"`([A-Z][A-Z0-9_]*)`", cells[1]))

    return names


def cabinet_variables() -> set[str]:
    """Variables the cabinet's own code reads (`process.env` passed as `env`).

    Tests and their helpers (`web/src/test/`, e.g. FC_SEED of the property
    tests) are not the cabinet's code and configure no deployment.
    """

    names: set[str] = set()
    test_helpers: Path = ROOT / "web" / "src" / "test"
    for path in (ROOT / "web" / "src").rglob("*.ts*"):
        if ".test." not in path.name and not path.is_relative_to(test_helpers):
            source: str = path.read_text(encoding="utf-8")
            names.update(re.findall(r"\benv\.([A-Z][A-Z0-9_]*)", source))

    return names - NEXT_JS_VARIABLES


README: str = "README.md"
