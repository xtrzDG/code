"""
A release writes only enum values the release before it already reads.

The previous release reads what this one writes during a deploy (and this
one reads the previous release's rows after a rollback); an enum value it
does not know fails the whole document. The enum values of every stored
document (the recorded shapes in tests/storage/document_schemas) are
compared with the snapshot of the last release
(tests/storage/release_enums.json, `record_release_enums`): a value that
release lacks must sit behind a closed release gate
(app/utilities/storage/release_gates.py), which storage refuses to write
until the next release opens it. Policy: docs/operations/deploys.md.
"""

import subprocess  # nosec B404 - git, with fixed arguments

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.monitoring import PlatformAlertStateRepoContract
from app.repositories.platform_alert_state_repository import (
    PlatformAlertStateRepository,
)
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from app.utilities.storage.release_gates import RELEASE_GATES
from tests.storage.document_evolution.enum_snapshot import (
    DocumentEnums,
    current_enums,
    enums_at,
    git,
    load_snapshot,
    snapshot_enums,
)
from tests.storage.document_evolution.sample_documents import sample_document

# Enum fields that are the key of their document: a release reads such
# documents only by the keys it knows, so it never meets a newer value.
KEYED_ENUM_FIELDS: dict[tuple[str, str], str] = {
    ("PlatformAlertStateDocument", "code"): (
        "alert states are stored under their code and read by the codes a "
        "release checks (`get_many`)"
    ),
}
COLLECTION_OF: dict[str, str] = {
    definition.document_type.__name__: str(definition.name)
    for definition in DOCUMENT_COLLECTIONS
}

type NewValue = tuple[str, str, str]


def values_the_last_release_lacks(
    now: DocumentEnums, before: DocumentEnums
) -> set[NewValue]:
    """(document, path, value) of enums both releases have, new since."""

    return {
        (document, path, value)
        for document, enums in now.items()
        for path, values in enums.items()
        if path in before.get(document, {})
        for value in set(values) - set(before[document][path])
    }


def gated_values() -> set[NewValue]:
    """What the closed gates of this release cover."""

    documents: dict[str, list[str]] = {}
    for document, collection in COLLECTION_OF.items():
        documents.setdefault(collection, []).append(document)
    return {
        (document, str(gate.path), str(value))
        for gate in RELEASE_GATES
        if not gate.is_open
        for document in documents.get(str(gate.collection_name), [])
        for value in gate.values
    }


def test_new_enum_values_sit_behind_a_closed_release_gate() -> None:
    new: set[NewValue] = values_the_last_release_lacks(
        current_enums(), snapshot_enums()
    )
    unexplained = sorted(
        (document, path, value)
        for document, path, value in new - gated_values()
        if (document, path) not in KEYED_ENUM_FIELDS
    )

    assert unexplained == [], (
        f"The release {load_snapshot()['release']} cannot read these values "
        "yet: list them behind a closed gate in "
        "app/utilities/storage/release_gates.py (and write them only once a "
        "later release opened it): " + ", ".join(map(str, unexplained))
    )


def test_a_closed_gate_covers_only_values_the_last_release_lacks() -> None:
    before: DocumentEnums = snapshot_enums()
    known: set[NewValue] = {
        (document, path, value)
        for document, enums in before.items()
        for path, values in enums.items()
        for value in values
    }

    stale = sorted(gated_values() & known)

    assert stale == [], (
        "The last release reads these values already: open their gates "
        f"(is_open=True): {stale}"
    )


def test_every_gate_names_a_stored_enum_of_its_collection() -> None:
    now: DocumentEnums = current_enums()
    for gate in RELEASE_GATES:
        documents = [
            document
            for document, collection in COLLECTION_OF.items()
            if collection == str(gate.collection_name)
        ]
        assert documents, gate.name
        for document in documents:
            assert set(map(str, gate.values)) <= set(
                now[document].get(str(gate.path), [])
            ), gate.name


def test_keyed_enum_fields_are_the_key_their_documents_are_read_by() -> None:
    collection = InMemoryDocumentCollectionAdapter[PlatformAlertStateDocument](
        PlatformAlertStateDocument
    )
    state = sample_document(
        PlatformAlertStateDocument, DocumentCollectionName("platform_alert_states")
    )
    PlatformAlertStateRepository(collection).save(state)
    reads: set[str] = {
        name
        for name in vars(PlatformAlertStateRepoContract)
        if not name.startswith("_")
    }

    assert collection.get(state.code.value) == state
    assert reads == {"get_many", "save"}, "A listing would meet unknown codes."
    assert set(KEYED_ENUM_FIELDS) == {("PlatformAlertStateDocument", "code")}


def test_the_snapshot_is_what_the_recorded_release_held() -> None:
    commit = str(load_snapshot()["commit"])
    try:
        git("cat-file", "-e", f"{commit}^{{commit}}")
    except OSError, subprocess.CalledProcessError:
        pytest.skip(f"the release commit {commit} is not in this clone")

    assert enums_at(commit) == snapshot_enums()
