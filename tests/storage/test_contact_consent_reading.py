"""
Every customer stored before marketing consent was kept (ContactDocument
version 4 and older) reads as one without consent: no campaign writes to
them until they agree.
"""

import pytest

from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from tests.storage.document_evolution.evolution_files import REPOSITORY_FILES

CONTACTS: DocumentCollectionName = DocumentCollectionName("contacts")


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_a_contact_from_before_consent_has_none(version: int) -> None:
    text: str = REPOSITORY_FILES.read_golden_text(CONTACTS, version)

    contact = PersistedDocumentCodec(ContactDocument, CONTACTS).decode(text)

    assert contact.marketing_consent is None
    assert not contact.has_marketing_consent


def test_the_current_version_keeps_the_recorded_consent() -> None:
    text: str = REPOSITORY_FILES.read_golden_text(CONTACTS, 5)

    contact = PersistedDocumentCodec(ContactDocument, CONTACTS).decode(text)

    assert contact.marketing_consent is not None
    assert str(contact.marketing_consent.text_version) == "2026-11-02"
