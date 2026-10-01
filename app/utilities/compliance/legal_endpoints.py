"""API paths of the legal documents shipped with the product."""

from app.schemas.typings.compliance.constrained_strings import (
    DpaDocumentUrl,
    DpaDocumentVersion,
)

DPA_DOCUMENT_ROUTE: str = "/v1/legal/dpa/{version}"


def build_dpa_document_url(version: DpaDocumentVersion) -> DpaDocumentUrl:
    """ "/v1/legal/dpa/2026-10-01": where the text of that version is served."""

    return DpaDocumentUrl(DPA_DOCUMENT_ROUTE.format(version=version))
