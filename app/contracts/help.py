"""The help center's articles and what each person has seen of the guidance."""

from collections.abc import Callable
from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.dto.help import HelpArticleRecord
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class HelpArticleRegistryContract(RegistryContract, Protocol):
    """Help articles shipped with the product, one set per language."""

    def available_languages(self) -> list[LanguageTag]:
        """The languages the help center is written in, sorted."""
        raise NotImplementedError

    def serve_language(self, requested: LanguageTag) -> LanguageTag | None:
        """
        The language to answer in: the one asked for, else its base
        language, else English, else any; None when there are no articles.
        """
        raise NotImplementedError

    def list_articles(self, language: LanguageTag) -> list[HelpArticleRecord]:
        """Every article of a served language, in no particular order."""
        raise NotImplementedError


class HelpProgressRepoContract(RepoContract, Protocol):
    def find(self, user_id: UserId) -> HelpProgressDocument | None:
        raise NotImplementedError

    def save(self, progress: HelpProgressDocument) -> None:
        raise NotImplementedError

    def change(
        self,
        user_id: UserId,
        change: Callable[[HelpProgressDocument], HelpProgressDocument | None],
        empty: HelpProgressDocument,
    ) -> HelpProgressDocument:
        """
        Apply `change` to the person's row in one atomic step, starting
        from `empty` when there is none; returns the row as stored.
        """
        raise NotImplementedError
