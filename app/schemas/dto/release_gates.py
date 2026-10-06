"""
Release gates: enum values a release already reads but does not write yet
(docs/operations/deploys.md, "Enum values one release ahead").
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.maintenance.booleans import IsReleaseGateOpen
from app.schemas.typings.maintenance.constrained_strings import (
    GatedEnumValue,
    ReleaseGateName,
    StoredEnumPath,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName


class ReleaseGate(ImmutableDTO):
    """
    The `values` of the enum field at `path` of a collection's documents.
    The release that adds them ships the gate closed: it reads the values
    (a later release, or a rollback, may hand it such documents) but writes
    none. The next release opens the gate, because the release before it
    then knows the values. Storage refuses to write a value of a closed
    gate.
    """

    name: ReleaseGateName
    collection_name: DocumentCollectionName
    path: StoredEnumPath
    values: list[GatedEnumValue]
    is_open: IsReleaseGateOpen
