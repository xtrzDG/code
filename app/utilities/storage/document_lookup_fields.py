"""
The lookup fields of every document collection: the only fields storage
queries may filter or sort by.

Migration 1010 gives each TEXT and INTEGER field a generated column
`doc_<field>` with a btree index, and each ELEMENT_TEXT field a trigger that
keeps its values in `workshop.document_lookup_keys`. Plain columns matter:
every table has forced row-level security, and Postgres uses an index under
RLS only for leakproof conditions; `document ->> 'field' = $1` is not one
(the JSON operator is not leakproof), `doc_field = $1` is. A test checks
that the database has a column or trigger for every field declared in
`document_lookup_catalog`.

`business_id` is a lookup field of every document type that has that field;
it is the table's own `business_id` column.
"""

from collections.abc import Iterable, Mapping

from base_pydantic_schemas import PersistentDocument

from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_queries import DocumentLookup, DocumentLookupField
from app.schemas.exceptions.storage_errors import UndeclaredLookupFieldError
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    DocumentFieldPath,
)
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.document_lookup_catalog import DOCUMENT_LOOKUP_FIELDS
from app.utilities.storage.document_tenancy import BUSINESS_ID_FIELD_NAME

BUSINESS_ID_FIELD: DocumentFieldPath = DocumentFieldPath(BUSINESS_ID_FIELD_NAME)
MATCH_KINDS: frozenset[LookupFieldKind] = frozenset(
    {LookupFieldKind.TEXT, LookupFieldKind.FILTER_TEXT, LookupFieldKind.ELEMENT_TEXT}
)
SELECTIVE_MATCH_KINDS: frozenset[LookupFieldKind] = frozenset(
    {LookupFieldKind.TEXT, LookupFieldKind.ELEMENT_TEXT}
)
RANGE_KINDS: frozenset[LookupFieldKind] = frozenset({LookupFieldKind.INTEGER})


def declared_lookup_fields(
    collection_name: DocumentCollectionName | None,
    document_type: type[PersistentDocument],
) -> dict[DocumentFieldPath, LookupFieldKind]:
    """
    The lookup fields of a collection: the declared ones and `business_id`
    when the document type has it. A collection outside the catalog (a test
    document type) has only `business_id`.
    """

    fields: dict[DocumentFieldPath, LookupFieldKind] = {}
    if BUSINESS_ID_FIELD_NAME in document_type.model_fields:
        fields[BUSINESS_ID_FIELD] = LookupFieldKind.TEXT

    declared: Iterable[DocumentLookupField] = (
        ()
        if collection_name is None
        else DOCUMENT_LOOKUP_FIELDS.get(collection_name, ())
    )
    for field in declared:
        fields[field.path] = field.kind

    return fields


def catalog_name_of(
    document_type: type[PersistentDocument],
) -> DocumentCollectionName | None:
    """The catalog collection of a document type, None for other types."""

    for definition in DOCUMENT_COLLECTIONS:
        if definition.document_type is document_type:
            return definition.name

    return None


def require_valid_lookup(
    fields: Mapping[DocumentFieldPath, LookupFieldKind],
    lookup: DocumentLookup,
    collection_label: str,
) -> None:
    """
    UndeclaredLookupFieldError unless every match is a TEXT, FILTER_TEXT or
    ELEMENT_TEXT lookup field, the range and order are INTEGER lookup
    fields, and FILTER_TEXT fields come with an indexed match (other than
    `business_id`) or a range that selects the rows they narrow.
    """

    match_kinds: list[LookupFieldKind] = [
        require_lookup_field(fields, match.field, MATCH_KINDS, collection_label)
        for match in lookup.matches
    ]
    if lookup.within is not None:
        require_lookup_field(fields, lookup.within.field, RANGE_KINDS, collection_label)

    if lookup.order is not None:
        require_lookup_field(fields, lookup.order.field, RANGE_KINDS, collection_label)

    is_selected_by_index: bool = lookup.within is not None or any(
        kind in SELECTIVE_MATCH_KINDS and match.field != BUSINESS_ID_FIELD
        for match, kind in zip(lookup.matches, match_kinds, strict=True)
    )
    if LookupFieldKind.FILTER_TEXT in match_kinds and not is_selected_by_index:
        raise UndeclaredLookupFieldError(
            f"Filter fields of {collection_label} only narrow a query by an "
            "indexed lookup field; add one."
        )


def require_lookup_field(
    fields: Mapping[DocumentFieldPath, LookupFieldKind],
    field: DocumentFieldPath,
    allowed_kinds: frozenset[LookupFieldKind],
    collection_label: str,
) -> LookupFieldKind:
    kind: LookupFieldKind | None = fields.get(field)
    if kind is None or kind not in allowed_kinds:
        expected: str = " or ".join(sorted(kind.value for kind in allowed_kinds))
        raise UndeclaredLookupFieldError(
            f"{field!s} is not a {expected} lookup field of {collection_label}; "
            "declare and index it (app/utilities/storage/document_lookup_catalog.py "
            "and a migration) before querying by it."
        )

    return kind


def split_element_path(field: DocumentFieldPath) -> tuple[str, str]:
    """`members[].user_id` -> ("members", "user_id")."""

    list_field, element_field = str(field).split("[].", maxsplit=1)
    return list_field, element_field
