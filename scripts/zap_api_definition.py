"""
The API definition the ZAP baseline of /v1 imports (.github/workflows/zap.yml),
cut from the committed web/openapi.json:

    uv run --no-project python -m scripts.zap_api_definition web/openapi.json \\
        --server http://localhost:8000 --business-id "$BUSINESS_ID" > zap/api.json

- only GET operations: a baseline scan reads and never writes, so importing
  the definition (ZAP calls every operation once) changes nothing;
- no event streams (`text/event-stream` answers never end);
- the seeded business's id in place of `{business_id}`, so the
  business-scoped routes answer as they do for their owner instead of 404;
- the stack's address as the only server.
"""

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

BUSINESS_PARAMETER: str = "business_id"
STREAM_MEDIA_TYPE: str = "text/event-stream"
BUSINESS_ID_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_stream(operation: dict[str, Any]) -> bool:
    for response in operation.get("responses", {}).values():
        if STREAM_MEDIA_TYPE in response.get("content", {}):
            return True
    return False


def without_business_parameter(
    parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        parameter
        for parameter in parameters
        if not (
            parameter.get("in") == "path"
            and parameter.get("name") == BUSINESS_PARAMETER
        )
    ]


def read_only_definition(
    definition: dict[str, Any], server: str, business_id: str
) -> dict[str, Any]:
    """The GET operations of `definition`, ready for ZAP's OpenAPI import."""

    paths: dict[str, Any] = {}
    for path, item in definition["paths"].items():
        operation: dict[str, Any] | None = item.get("get")
        if operation is None or is_stream(operation):
            continue

        scanned: dict[str, Any] = dict(operation)
        resolved_path: str = path
        if "{" + BUSINESS_PARAMETER + "}" in path:
            resolved_path = path.replace("{" + BUSINESS_PARAMETER + "}", business_id)
            scanned["parameters"] = without_business_parameter(
                operation.get("parameters", [])
            )
        shared: list[dict[str, Any]] = without_business_parameter(
            item.get("parameters", [])
        )
        paths[resolved_path] = {"get": scanned} | (
            {"parameters": shared} if shared else {}
        )

    return {
        "openapi": definition["openapi"],
        "info": definition["info"],
        "servers": [{"url": server}],
        "paths": paths,
        "components": definition.get("components", {}),
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.zap_api_definition",
        description="The read-only part of the API definition, for ZAP's API baseline.",
    )
    parser.add_argument("definition", type=Path, help="web/openapi.json")
    parser.add_argument(
        "--server", required=True, help="the API's address, e.g. http://localhost:8000"
    )
    parser.add_argument("--business-id", required=True, help="the seeded business")
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parsed: argparse.Namespace = build_argument_parser().parse_args(arguments)
    if not parsed.server.startswith(("http://", "https://")):
        print("--server must be an http(s) address.", file=sys.stderr)
        return 2
    if BUSINESS_ID_PATTERN.fullmatch(parsed.business_id) is None:
        print("--business-id is not a business id.", file=sys.stderr)
        return 2
    try:
        definition: dict[str, Any] = json.loads(
            parsed.definition.read_text(encoding="utf-8")
        )
        result = read_only_definition(
            definition, parsed.server.rstrip("/"), parsed.business_id
        )
    except (OSError, ValueError, KeyError) as error:
        print(
            f"{parsed.definition}: not a usable OpenAPI definition ({error})",
            file=sys.stderr,
        )
        return 2

    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
