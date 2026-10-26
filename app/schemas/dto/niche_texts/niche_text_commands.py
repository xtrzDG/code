"""Requests and commands of the platform admin's niche template editor."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.niches import NicheKey
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.schemas.typings.users.prefixed_id import UserId

# More than every editable text of the largest niche (about sixty).
MAX_DRAFT_TEXTS: int = 300


class NicheTextOverviewQuery(ImmutableDTO):
    """Every niche's override state; names in `language` (English if None)."""

    user_id: UserId
    language: LanguageTag | None = None


class NicheTextEditorQuery(ImmutableDTO):
    """One niche's editor in `language` (English if None)."""

    user_id: UserId
    niche_key: NicheKey
    language: LanguageTag | None = None


class NicheTextHistoryQuery(ImmutableDTO):
    """A niche's published versions."""

    user_id: UserId
    niche_key: NicheKey


class NicheTextInput(ImmutableDTO):
    """The admin's wording of one field."""

    field_key: NicheTextFieldKey
    text: NicheOverrideText


class SaveNicheTextDraftRequest(ImmutableDTO):
    """
    The draft's texts in one language: they replace the draft's texts of
    that language; a field left out keeps the code's text.
    """

    language: LanguageTag
    texts: list[NicheTextInput] = Field(
        default_factory=list[NicheTextInput], max_length=MAX_DRAFT_TEXTS
    )


class SaveNicheTextDraftCommand(ImmutableDTO):
    user_id: UserId
    niche_key: NicheKey
    language: LanguageTag
    texts: list[NicheTextInput] = Field(
        default_factory=list[NicheTextInput], max_length=MAX_DRAFT_TEXTS
    )


class NicheTextCommand(ImmutableDTO):
    """Publish the draft of a niche, or discard it."""

    user_id: UserId
    niche_key: NicheKey
    client_ip_address: ClientIpAddress | None = None


class RevertNicheTextsRequest(ImmutableDTO):
    """Publish again the texts of `version` (0: the code template's own)."""

    version: NicheTextVersion


class RevertNicheTextsCommand(ImmutableDTO):
    user_id: UserId
    niche_key: NicheKey
    version: NicheTextVersion
    client_ip_address: ClientIpAddress | None = None
