"""
Validating bodies against the vendored specifications (tests/contracts/specs).

`assert_inbound` checks what a provider sends or answers (fixtures):
vendors add fields freely, so the schemas stay open. `assert_outbound`
checks what the platform sends, with every object closed
(`schema_closure`): a field the vendor does not define fails the test.
"""

import functools
import json
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match

from tests.contracts.contract_files import SPECS_DIRECTORY
from tests.contracts.schema_closure import JsonObject, closed_definitions

MAX_REPORTED_ERRORS: int = 6


@functools.cache
def load_spec(file_name: str) -> JsonObject:
    parsed: object = json.loads((SPECS_DIRECTORY / file_name).read_text("utf-8"))
    return cast(JsonObject, parsed)


@functools.cache
def spec_validator(file_name: str, root: str, closed: bool) -> Draft202012Validator:
    spec: JsonObject = load_spec(file_name)
    roots: JsonObject = cast(JsonObject, spec["x-roots"])
    if root not in roots:
        raise KeyError(f"{file_name} has no root {root!r}: {sorted(roots)}")

    definitions: JsonObject = cast(JsonObject, spec["$defs"])
    return Draft202012Validator(
        {
            "$schema": spec["$schema"],
            "$defs": closed_definitions(definitions) if closed else definitions,
            "$ref": "#/$defs/" + root.replace("~", "~0").replace("/", "~1"),
        }
    )


def validation_problems(
    instance: Any, file_name: str, root: str, closed: bool = False
) -> list[str]:
    """Readable problems of the instance (empty when it matches)."""

    validator: Draft202012Validator = spec_validator(file_name, root, closed)
    errors: list[ValidationError] = list(validator.iter_errors(instance))
    if not errors:
        return []

    best: ValidationError | None = best_match(errors)
    ranked: list[ValidationError] = sorted(
        errors, key=lambda error: -len(list(error.absolute_path))
    )
    chosen: list[ValidationError] = ([best] if best is not None else []) + ranked
    return [
        f"at /{'/'.join(str(part) for part in error.absolute_path)}: "
        f"{error.message[:300]}"
        for error in chosen[:MAX_REPORTED_ERRORS]
    ]


def assert_inbound(instance: Any, file_name: str, root: str) -> None:
    problems: list[str] = validation_problems(instance, file_name, root)
    assert problems == [], f"{file_name} {root}:\n" + "\n".join(problems)


def assert_outbound(instance: Any, file_name: str, root: str) -> None:
    problems: list[str] = validation_problems(instance, file_name, root, closed=True)
    assert problems == [], f"{file_name} {root} (closed):\n" + "\n".join(problems)
