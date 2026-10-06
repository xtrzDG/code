"""What a vendored specification is made of: its source, roots and patches."""

from dataclasses import dataclass
from enum import StrEnum

type JsonValue = object
type JsonObject = dict[str, object]


class DocumentFormat(StrEnum):
    """How a vendor publishes its machine-readable description."""

    OPENAPI = "openapi"
    GOOGLE_DISCOVERY = "google-discovery"
    # The types of an installed SDK the vendor generates from its own
    # specification (Stainless for Anthropic): read with pydantic.
    PYTHON_SDK = "python-sdk"


@dataclass(frozen=True)
class SchemaRoot:
    """
    One schema the tests validate against, under `name` in the file.

    `selector` says where it is in the vendor document:
    - "schema:<Name>": a named component schema (OpenAPI, discovery);
    - "request:<METHOD> <path>": an operation's request body (JSON first,
      then form fields);
    - "response:<METHOD> <path> <status>": an operation's JSON response;
    - "python:<module>:<type>": a type of an installed SDK.
    """

    name: str
    selector: str


@dataclass(frozen=True)
class RepairSectionReferences:
    """
    Meta's merged document renames colliding schemas of later sections
    with a suffix ("TextMessage_2") but leaves their references on the
    first section's names. From `first_schema` on, a reference to a name
    whose suffixed twin is defined in the same section is pointed at it.
    Applied to the vendor document before extraction.
    """

    first_schema: str
    reason: str


@dataclass(frozen=True)
class DropRequired:
    """The vendor marks a field required that its API does not require."""

    definition: str
    property_name: str
    reason: str


@dataclass(frozen=True)
class AddProperty:
    """A documented field the published specification has not caught up with."""

    definition: str
    property_name: str
    schema: JsonObject
    reason: str


@dataclass(frozen=True)
class DropProperty:
    """A field of an SDK type that travels outside the body (a header)."""

    definition: str
    property_name: str
    reason: str


@dataclass(frozen=True)
class DropPropertyKeyword:
    """A constraint of one property that the vendor wrote wrongly."""

    definition: str
    property_name: str
    keyword: str
    reason: str


type DefinitionPatch = DropRequired | AddProperty | DropProperty | DropPropertyKeyword
type SpecPatch = RepairSectionReferences | DefinitionPatch


@dataclass(frozen=True)
class VendorSpec:
    """One vendored file: `tests/contracts/specs/<file_name>`."""

    file_name: str
    provider: str
    title: str
    source_url: str
    document_format: DocumentFormat
    roots: tuple[SchemaRoot, ...]
    patches: tuple[SpecPatch, ...] = ()
