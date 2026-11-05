"""
What every step of the niche template editor shares: the niche's editable
texts from the code, its newest version and draft, the entries compared
and ordered, and the names of the admins who published.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.contracts.platform_admins import PlatformAdminCheck
from app.contracts.registries import NicheTemplateRegistryContract
from app.contracts.repositories.niche_text_repositories import NicheTextRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.starter_registries import StarterAnswerRegistryContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextEntry,
    NicheTextReleaseDocument,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.niche_texts.niche_text_fields import NicheTextCatalog
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.niches.constrained_strings import NicheTextFieldKey
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName
from app.utilities.niches.niche_text_catalog import build_niche_text_catalog
from app.utilities.niches.niche_text_checks import EDITABLE_LANGUAGES

# The starter answers' texts are the same in every country (only the
# weekend of their opening hours differs), so any country reads them.
TEXT_COUNTRY: CountryCode = CountryCode("GE")

type EntryKey = tuple[str, str, str]


@dataclass(frozen=True, slots=True, kw_only=True)
class NicheTextSources:
    """The code's templates and starter answers, and the stored overrides."""

    niche_templates: NicheTemplateRegistryContract
    starter_answers: StarterAnswerRegistryContract
    niche_text_repo: NicheTextRepoContract

    def catalog(self, niche_key: NicheKey) -> NicheTextCatalog:
        """Every editable text of the niche as the code writes it."""

        return build_niche_text_catalog(
            self.niche_templates.get(niche_key),
            self.starter_answers.get(niche_key, TEXT_COUNTRY),
        )

    def latest(self, niche_key: NicheKey) -> NicheTextReleaseDocument | None:
        """The version in force (None: the code template, version 0)."""

        for release in self.niche_text_repo.latest_releases([niche_key]):
            return release

        return None


def published_entries(release: NicheTextReleaseDocument | None) -> list[NicheTextEntry]:
    return [] if release is None else list(release.entries)


def same_entries(
    first: Sequence[NicheTextEntry], second: Sequence[NicheTextEntry]
) -> bool:
    """Whether both sets override the same fields with the same words."""

    return entry_keys(first) == entry_keys(second)


def entry_keys(entries: Iterable[NicheTextEntry]) -> set[EntryKey]:
    return {
        (str(entry.field_key), str(entry.language), str(entry.text))
        for entry in entries
    }


def is_unpublished(
    draft: NicheTextDraftDocument | None, release: NicheTextReleaseDocument | None
) -> bool:
    """Whether a draft waits that differs from the version in force."""

    return draft is not None and not same_entries(
        draft.entries, published_entries(release)
    )


def ordered_entries(
    catalog: NicheTextCatalog, entries: Iterable[NicheTextEntry]
) -> list[NicheTextEntry]:
    """In the editor's order: field by field, the cabinet's languages in order."""

    field_order: dict[NicheTextFieldKey, int] = {
        field.field_key: position for position, field in enumerate(catalog.fields)
    }
    language_order: dict[LanguageTag, int] = {
        language: position for position, language in enumerate(EDITABLE_LANGUAGES)
    }
    return sorted(
        entries,
        key=lambda entry: (
            field_order.get(entry.field_key, len(field_order)),
            language_order.get(entry.language, len(language_order)),
        ),
    )


def display_names(
    user_repo: UserRepoContract, user_ids: Iterable[UserId]
) -> dict[UserId, UserDisplayName]:
    """The names of these admins (those without a name left out), one read."""

    wanted: list[UserId] = list(dict.fromkeys(user_ids))
    if not wanted:
        return {}

    return {
        user.id: user.display_name
        for user in user_repo.get_many(wanted)
        if user.display_name is not None
    }


def authorize_editor(check: PlatformAdminCheck, user_id: UserId) -> UserDocument:
    """The admin, when their role may manage the niche templates (SUPER)."""

    return check.run(
        PlatformAdminAccessRequest(
            user_id=user_id, permission=PlatformAdminPermission.MANAGE_NICHE_TEMPLATES
        )
    )
