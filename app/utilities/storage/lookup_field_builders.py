"""The lookup fields of the catalogs, one builder per kind of lookup field."""

from app.schemas.constants.storage import LookupFieldKind
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath


def text_field(path: str) -> DocumentLookupField:
    return DocumentLookupField(path=DocumentFieldPath(path), kind=LookupFieldKind.TEXT)


def filter_field(path: str) -> DocumentLookupField:
    return DocumentLookupField(
        path=DocumentFieldPath(path), kind=LookupFieldKind.FILTER_TEXT
    )


def integer_field(path: str) -> DocumentLookupField:
    return DocumentLookupField(
        path=DocumentFieldPath(path), kind=LookupFieldKind.INTEGER
    )


def element_field(path: str) -> DocumentLookupField:
    return DocumentLookupField(
        path=DocumentFieldPath(path), kind=LookupFieldKind.ELEMENT_TEXT
    )
