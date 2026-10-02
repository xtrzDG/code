"""The declared lookup fields name real document fields of the right kind."""

import typing

from base_pydantic_schemas import BaseDocument, PersistentDocument

from app.schemas.constants.storage import LookupFieldKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.document_lookup_catalog import DOCUMENT_LOOKUP_FIELDS
from app.utilities.storage.document_lookup_fields import (
    BUSINESS_ID_FIELD,
    catalog_name_of,
    declared_lookup_fields,
    split_element_path,
)

INTEGER_NAMES: frozenset[str] = frozenset(
    {
        "BookingEndsAtUnixSeconds",
        "BookingStartsAtUnixSeconds",
        "CostMicroUsd",
        "LlmTokenCount",
        "LlmTurnSequenceNumber",
        "Microseconds",
        "QuestionOccurrenceCount",
    }
)


class LooseNote(BaseDocument):
    """A document type outside the catalog, owned by a business."""

    business_id: BusinessId


class PlatformNote(BaseDocument):
    """A document type outside the catalog without a business."""


def field_annotation(document_type: type[PersistentDocument], name: str) -> object:
    field = document_type.model_fields.get(name)
    assert field is not None, f"{document_type.__name__} has no field {name!r}"
    return field.annotation


def unwrap_optional(annotation: object) -> object:
    arguments = [a for a in typing.get_args(annotation) if a is not type(None)]
    return arguments[0] if len(arguments) == 1 else annotation


def test_every_declared_field_exists_with_the_declared_kind() -> None:
    types = {
        definition.name: definition.document_type for definition in DOCUMENT_COLLECTIONS
    }

    for collection_name, fields in DOCUMENT_LOOKUP_FIELDS.items():
        document_type = types[collection_name]
        for field in fields:
            if field.kind is LookupFieldKind.ELEMENT_TEXT:
                list_field, element_field = split_element_path(field.path)
                list_type = field_annotation(document_type, list_field)
                (element_type,) = typing.get_args(list_type)
                field_annotation(element_type, element_field)
                continue

            annotation = unwrap_optional(
                field_annotation(document_type, str(field.path))
            )
            is_integer = getattr(annotation, "__name__", "") in INTEGER_NAMES
            assert is_integer == (field.kind is LookupFieldKind.INTEGER), field


def test_business_id_is_a_lookup_field_of_every_type_that_has_it() -> None:
    contact_fields = declared_lookup_fields(
        catalog_name_of(ContactDocument), ContactDocument
    )
    business_fields = declared_lookup_fields(
        catalog_name_of(BusinessDocument), BusinessDocument
    )

    assert contact_fields[BUSINESS_ID_FIELD] is LookupFieldKind.TEXT
    assert BUSINESS_ID_FIELD not in business_fields
    assert business_fields == {
        DocumentFieldPath("members[].user_id"): LookupFieldKind.ELEMENT_TEXT
    }


def test_types_outside_the_catalog_have_only_their_business() -> None:
    assert catalog_name_of(LooseNote) is None
    assert declared_lookup_fields(None, LooseNote) == {
        BUSINESS_ID_FIELD: LookupFieldKind.TEXT
    }
    assert declared_lookup_fields(None, PlatformNote) == {}


def test_element_paths_split_into_list_and_element_fields() -> None:
    assert split_element_path(DocumentFieldPath("members[].user_id")) == (
        "members",
        "user_id",
    )
