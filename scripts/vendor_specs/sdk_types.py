"""
Roots from the types of an installed SDK (`DocumentFormat.PYTHON_SDK`).

Anthropic and ElevenLabs generate their Python SDKs from their own API
specifications (Stainless, Fern); where the specification itself is not
published, the SDK's types are the machine-readable description at hand,
read with pydantic.

- "python:<module>:<Type>": a type (a TypedDict, a pydantic model);
- "python-body:<module>:<Class>.<method>": the JSON body the method sends,
  read from its `json={...}` argument: Fern clients take body fields,
  query parameters and headers as one list of keyword arguments.

Fern models allow undeclared fields (`extra="allow"`, so an old SDK keeps
reading newer answers). That says nothing about the API, so the marker is
dropped and outbound bodies are closed like those of the other vendors.
"""

import ast
import importlib
import inspect
import textwrap
import typing
from collections.abc import Callable, Mapping
from typing import cast

from pydantic import TypeAdapter

from scripts.vendor_specs.spec_model import JsonObject, JsonValue, SchemaRoot

REFERENCE_TEMPLATE: str = "#/$defs/{model}"
BODY_ARGUMENT: str = "json"

type SdkRoots = tuple[dict[str, JsonValue], dict[str, JsonValue]]


class SdkSelectorError(ValueError):
    """A selector that names nothing the installed SDK has."""


def sdk_roots(roots: tuple[SchemaRoot, ...]) -> SdkRoots:
    """The raw roots and the named schemas pydantic gave their shared parts."""

    raw_roots: dict[str, JsonValue] = {}
    components: dict[str, JsonValue] = {}
    for root in roots:
        schema: JsonObject = cast(JsonObject, without_extra_allowance(sdk_schema(root)))
        definitions: object = schema.pop("$defs", {})
        for name, definition in cast(JsonObject, definitions).items():
            if components.get(name, definition) != definition:
                raise SdkSelectorError(f"{name} differs between the SDK's types.")
            components[name] = definition

        raw_roots[root.name] = schema

    return raw_roots, components


def sdk_schema(root: SchemaRoot) -> JsonObject:
    kind, module_name, target = root.selector.split(":")
    module: object = importlib.import_module(module_name)
    if kind == "python":
        return type_schema(getattr(module, target))

    if kind == "python-body":
        class_name, _, method_name = target.partition(".")
        method: object = getattr(getattr(module, class_name), method_name)
        return request_body_schema(cast(Callable[..., object], method))

    raise SdkSelectorError(f"Unknown selector {root.selector!r}.")


def type_schema(sdk_type: object) -> JsonObject:
    return TypeAdapter(sdk_type).json_schema(ref_template=REFERENCE_TEMPLATE)


def request_body_schema(method: Callable[..., object]) -> JsonObject:
    """An object with the body fields the method sends, typed by its parameters."""

    hints: dict[str, object] = typing.get_type_hints(method)
    parameters: Mapping[str, inspect.Parameter] = inspect.signature(method).parameters
    properties: JsonObject = {}
    required: list[str] = []
    definitions: JsonObject = {}
    for field_name, parameter_name in body_parameters(method).items():
        schema: JsonObject = type_schema(hints[parameter_name])
        for name, definition in cast(JsonObject, schema.pop("$defs", {})).items():
            if definitions.get(name, definition) != definition:
                raise SdkSelectorError(f"{name} differs between body fields.")
            definitions[name] = definition

        properties[field_name] = schema
        if parameters[parameter_name].default is inspect.Parameter.empty:
            required.append(field_name)

    body: JsonObject = {"type": "object", "properties": properties}
    if required:
        body["required"] = required
    if definitions:
        body["$defs"] = definitions
    return body


def body_parameters(method: Callable[..., object]) -> dict[str, str]:
    """Body field -> the parameter it is sent from, in the order of the source."""

    parameter_names: set[str] = set(inspect.signature(method).parameters)
    tree: ast.Module = ast.parse(textwrap.dedent(inspect.getsource(method)))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.keyword)
            and node.arg == BODY_ARGUMENT
            and isinstance(node.value, ast.Dict)
        ):
            return {
                key.value: sent_parameter(value, parameter_names)
                for key, value in zip(node.value.keys, node.value.values, strict=True)
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }

    raise SdkSelectorError(f"{method.__qualname__} sends no json={{...}} body.")


def sent_parameter(value: ast.expr, parameter_names: set[str]) -> str:
    for node in ast.walk(value):
        if isinstance(node, ast.Name) and node.id in parameter_names:
            return node.id

    raise SdkSelectorError(f"A body field is not sent from a parameter: {value!r}.")


def without_extra_allowance(node: JsonValue) -> JsonValue:
    """The schema without `additionalProperties: true` beside declared fields."""

    if isinstance(node, list):
        return [without_extra_allowance(item) for item in cast(list[JsonValue], node)]

    if not isinstance(node, dict):
        return node

    source: JsonObject = cast(JsonObject, node)
    cleaned: JsonObject = {
        key: without_extra_allowance(value) for key, value in source.items()
    }
    if cleaned.get("additionalProperties") is True and "properties" in cleaned:
        del cleaned["additionalProperties"]
    return cleaned
