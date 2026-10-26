"""
The id of a published version of a niche's texts: derived from the niche
and the version, so the version is stored once whoever publishes it. The
namespace is fixed: stored ids depend on it.
"""

from uuid import UUID, uuid5

from app.schemas.constants.niches import NicheKey
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.niches.prefixed_id import NicheTextReleaseId

NICHE_TEXT_RELEASE_NAMESPACE: UUID = UUID("0b8b7a52-2b4e-4b8e-9f43-6c1f1d7e5a20")


def release_id_for(
    niche_key: NicheKey, version: NicheTextVersion
) -> NicheTextReleaseId:
    return NicheTextReleaseId(
        uuid5(NICHE_TEXT_RELEASE_NAMESPACE, f"{niche_key.value}:{int(version)}")
    )
