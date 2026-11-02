"""Hypothesis strategies of requests to one documented API operation."""

from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import quote

from hypothesis import strategies as st

type JsonObject = dict[str, Any]

HTTP_METHODS: tuple[str, ...] = ("get", "post", "put", "patch", "delete")
# Streams never end on their own: their routes have tests of their own.
STREAM_MEDIA_TYPE: str = "text/event-stream"
# Path segments: ids of all shapes, words, markup, other scripts.
SEGMENT_TEXT = st.one_of(
    st.text(
        alphabet=st.characters(codec="utf-8", exclude_characters="/"),
        min_size=1,
        max_size=40,
    ),
    st.sampled_from(["0", "-1", "null", "business_0", "x" * 300, "%00", "..", "<a>"]),
)
JSON_SCALARS = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**63), max_value=2**63),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=60),
)
JSON_VALUES = st.recursive(
    JSON_SCALARS,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(max_size=12), children, max_size=4),
    ),
    max_leaves=12,
)


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    path_parameters: tuple[str, ...]
    query_parameters: tuple[str, ...]
    body_fields: tuple[str, ...] | None

    @property
    def label(self) -> str:
        return f"{self.method.upper()} {self.path}"


@dataclass(frozen=True)
class FuzzRequest:
    path: str
    params: dict[str, str]
    body: object


def documented_operations(description: JsonObject) -> list[Operation]:
    """Every operation of the description, streams left out."""

    found: list[Operation] = []
    for path, item in cast(dict[str, JsonObject], description["paths"]).items():
        for method in HTTP_METHODS:
            operation: JsonObject | None = item.get(method)
            if operation is None or is_stream(operation):
                continue

            parameters: list[JsonObject] = operation.get("parameters", [])
            found.append(
                Operation(
                    method=method,
                    path=path,
                    path_parameters=names_in(parameters, "path"),
                    query_parameters=names_in(parameters, "query"),
                    body_fields=body_fields_of(operation),
                )
            )

    return found


def is_stream(operation: JsonObject) -> bool:
    responses: dict[str, JsonObject] = operation.get("responses", {})
    return any(
        STREAM_MEDIA_TYPE in (r.get("content") or {}) for r in responses.values()
    )


def names_in(parameters: list[JsonObject], location: str) -> tuple[str, ...]:
    return tuple(str(p["name"]) for p in parameters if p.get("in") == location)


def body_fields_of(operation: JsonObject) -> tuple[str, ...] | None:
    """The top-level fields of a JSON body; None without a body."""

    content: JsonObject = operation.get("requestBody", {}).get("content", {})
    schema: JsonObject | None = content.get("application/json", {}).get("schema")
    if schema is None:
        return None

    return tuple(str(name) for name in schema.get("properties", {}))


@st.composite
def requests_to(draw: st.DrawFn, operation: Operation, business_id: str) -> FuzzRequest:
    path: str = operation.path
    for name in operation.path_parameters:
        value: str = (
            draw(st.one_of(st.just(business_id), SEGMENT_TEXT))
            if name == "business_id"
            else draw(SEGMENT_TEXT)
        )
        path = path.replace("{" + name + "}", quote(value, safe=""))

    params: dict[str, str] = {
        name: draw(st.text(max_size=40))
        for name in operation.query_parameters
        if draw(st.booleans())
    }
    body: object = None
    if operation.body_fields is not None:
        fields = st.fixed_dictionaries(
            {}, optional={name: JSON_VALUES for name in operation.body_fields}
        )
        body = draw(st.one_of(fields, JSON_VALUES))

    return FuzzRequest(path=path, params=params, body=body)
