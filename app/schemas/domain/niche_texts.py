"""
The platform admin's overrides of the owner-facing texts of the niche
templates (R17-NICHE-TEMPLATE-EDITOR): a draft per niche and every
published version. Platform collections: they name no business.
"""

from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field

from app.schemas.constants.niches import NicheKey, NicheTextReleaseKind
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.schemas.typings.niches.prefixed_id import NicheTextReleaseId
from app.schemas.typings.users.prefixed_id import UserId


class NicheTextEntry(PersistentDocument):
    """The admin's wording of one field of a niche template in one language."""

    field_key: NicheTextFieldKey
    language: LanguageTag
    text: NicheOverrideText


class NicheTextDraftDocument(BaseDocument):
    """
    The texts an admin is preparing for a niche, stored under the niche's
    key: the whole override set the next version will publish (every
    language), not a change against the published one. Owners never see a
    draft; publishing, a revert and a reset remove it.
    """

    niche_key: NicheKey
    entries: list[NicheTextEntry] = Field(default_factory=list[NicheTextEntry])
    updated_by: UserId


class NicheTextReleaseDocument(BaseDocument):
    """
    One published version of a niche's overrides: the set in force from
    `created_at` until the next version. The newest version of a niche is
    what new owners read in the tunnel and the profile wizard (code
    template + these entries); profiles saved before keep their texts.
    `restored_version` names the version a REVERT went back to.
    """

    id: NicheTextReleaseId
    niche_key: NicheKey
    version: NicheTextVersion
    kind: NicheTextReleaseKind
    entries: list[NicheTextEntry] = Field(default_factory=list[NicheTextEntry])
    restored_version: NicheTextVersion | None = None
    published_by: UserId
