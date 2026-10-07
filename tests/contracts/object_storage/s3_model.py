"""
S3's service model as botocore ships it (the model every AWS SDK is
generated from; botocore comes with moto, a dev dependency): the XML the
clients read and send, and the query parameters they sign, are checked
against the operation shapes, so a renamed element or parameter fails here.

Only fixtures and the platform's own request bodies are parsed (no remote
input), so the standard library parser is enough.
"""

import functools
import gzip
import json
import re
from importlib.resources import files
from typing import Any, cast
from urllib.parse import parse_qsl, urlsplit
from xml.etree import ElementTree

import httpx

S3_MODEL_PATH: tuple[str, ...] = ("data", "s3", "2006-03-01", "service-2.json.gz")
NAMESPACE_PATTERN: re.Pattern[str] = re.compile(r"^\{[^}]*\}")
TIMESTAMP_PATTERN: re.Pattern[str] = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d")
# Signature Version 4 query authentication (the AWS signing documentation,
# not the service model) adds these to every presigned URL.
PRESIGNING_PARAMETERS: frozenset[str] = frozenset(
    {
        "X-Amz-Algorithm",
        "X-Amz-Credential",
        "X-Amz-Date",
        "X-Amz-Expires",
        "X-Amz-SignedHeaders",
        "X-Amz-Signature",
    }
)
TRANSPORT_HEADERS: frozenset[str] = frozenset(
    {"host", "accept", "accept-encoding", "connection", "user-agent", "content-length"}
)


@functools.cache
def s3_model() -> dict[str, Any]:
    compressed: bytes = files("botocore").joinpath(*S3_MODEL_PATH).read_bytes()
    return cast(dict[str, Any], json.loads(gzip.decompress(compressed)))


def shape(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], s3_model()["shapes"][name])


def operation(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], s3_model()["operations"][name])


def local_name(tag: str) -> str:
    return NAMESPACE_PATTERN.sub("", tag)


def parse_xml(text: str | bytes) -> ElementTree.Element:
    return ElementTree.fromstring(text)


def xml_problems(element: ElementTree.Element, shape_name: str, path: str) -> list[str]:
    """Every element below `element` that `shape_name` does not define."""

    definition: dict[str, Any] = shape(shape_name)
    kind: str = definition["type"]
    if kind != "structure":
        return scalar_problems(element, kind, path)

    members: dict[str, dict[str, Any]] = {
        member.get("locationName", name): member
        for name, member in cast(
            dict[str, dict[str, Any]], definition["members"]
        ).items()
        if "location" not in member
    }
    problems: list[str] = []
    for child in element:
        tag: str = local_name(child.tag)
        member: dict[str, Any] | None = members.get(tag)
        if member is None:
            problems.append(f"{path}/{tag}: {shape_name} has no such member")
            continue

        member_shape: dict[str, Any] = shape(member["shape"])
        if member_shape["type"] == "list" and member_shape.get("flattened"):
            problems += xml_problems(
                child, member_shape["member"]["shape"], f"{path}/{tag}"
            )
        else:
            problems += xml_problems(child, member["shape"], f"{path}/{tag}")
    return problems


def scalar_problems(element: ElementTree.Element, kind: str, path: str) -> list[str]:
    text: str = element.text or ""
    if len(element):
        return [f"{path}: a {kind} has no child elements"]
    if kind in {"integer", "long"} and not text.isdigit():
        return [f"{path}: {text!r} is not an {kind}"]
    if kind == "boolean" and text not in {"true", "false"}:
        return [f"{path}: {text!r} is not a boolean"]
    if kind == "timestamp" and not TIMESTAMP_PATTERN.match(text):
        return [f"{path}: {text!r} is not a timestamp"]
    return []


def assert_xml_matches(text: str | bytes, root_tag: str, shape_name: str) -> None:
    root: ElementTree.Element = parse_xml(text)
    assert local_name(root.tag) == root_tag
    problems: list[str] = xml_problems(root, shape_name, root_tag)
    assert not problems, "\n".join(problems)


def request_problems(request: httpx.Request, operation_name: str) -> list[str]:
    """What a request sends that the operation does not define."""

    definition: dict[str, Any] = operation(operation_name)
    members: list[dict[str, Any]] = list(
        shape(definition["input"]["shape"])["members"].values()
    )
    request_uri: str = definition["http"]["requestUri"]
    literal_query: set[str] = {
        name for name, _ in parse_qsl(urlsplit(request_uri).query, True)
    }
    query_names: set[str] = literal_query | {
        member["locationName"]
        for member in members
        if member.get("location") == "querystring"
    }
    header_names: set[str] = {
        str(member["locationName"]).lower()
        for member in members
        if member.get("location") == "header"
    }
    problems: list[str] = []
    if request.method != definition["http"]["method"]:
        problems.append(f"{operation_name} is a {definition['http']['method']}")
    sent_query: set[str] = {name for name, _ in request.url.params.multi_items()}
    problems += [
        f"{operation_name} has no query parameter {name!r}"
        for name in sorted(sent_query - query_names - PRESIGNING_PARAMETERS)
    ]
    problems += [
        f"{operation_name} needs the query parameter {name!r}"
        for name in sorted(literal_query - sent_query)
    ]
    problems += [
        f"{operation_name} has no header {name!r}"
        for name in sorted(set(request.headers.keys()) - TRANSPORT_HEADERS)
        if name not in header_names
    ]
    return problems
