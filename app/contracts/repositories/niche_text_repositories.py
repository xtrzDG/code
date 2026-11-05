"""The niche templates' text overrides: drafts and published versions."""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextReleaseDocument,
)
from app.schemas.typings.niches.constrained_integers import NicheTextVersion
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class NicheTextRepoContract(RepoContract, Protocol):
    """
    One draft per niche and every published version (platform collections,
    a few rows per niche). The newest version is read by indexed probes,
    never by reading a niche's whole history.
    """

    def get_draft(self, niche_key: NicheKey) -> NicheTextDraftDocument | None:
        raise NotImplementedError

    def list_drafts(
        self, niche_keys: Sequence[NicheKey]
    ) -> list[NicheTextDraftDocument]:
        """The drafts of these niches (those without one left out)."""
        raise NotImplementedError

    def save_draft(self, draft: NicheTextDraftDocument) -> None:
        raise NotImplementedError

    def delete_draft(self, niche_key: NicheKey) -> None:
        raise NotImplementedError

    def latest_releases(
        self, niche_keys: Sequence[NicheKey]
    ) -> list[NicheTextReleaseDocument]:
        """The newest version of each of these niches that has one."""
        raise NotImplementedError

    def get_release(
        self, niche_key: NicheKey, version: NicheTextVersion
    ) -> NicheTextReleaseDocument | None:
        raise NotImplementedError

    def add_release(self, release: NicheTextReleaseDocument) -> bool:
        """
        Store a new version in one atomic step: False, and nothing written,
        when the niche has this version already (two admins publishing at
        once).
        """
        raise NotImplementedError

    def list_releases(
        self, niche_key: NicheKey, limit: DocumentQueryLimit
    ) -> list[NicheTextReleaseDocument]:
        """A niche's newest `limit` versions, newest first."""
        raise NotImplementedError
