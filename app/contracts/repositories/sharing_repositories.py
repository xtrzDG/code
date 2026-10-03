"""
Persistence contracts of sharing the assistant: the public chat addresses
(`/c/{slug}`) businesses took.

Implementations return independent copies: mutating a returned document
does not change stored state until it is saved.
"""

from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.public_slugs import PublicSlugClaimDocument
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug


class PublicSlugClaimRepoContract(RepoContract, Protocol):
    def claim(self, claim: PublicSlugClaimDocument) -> bool:
        """
        Take an address for a business in one atomic step (also across
        processes); False, and nothing stored, when the address is already
        taken by any business (the caller checks whether that is its own).
        """
        raise NotImplementedError

    def get(self, slug: BusinessPublicSlug) -> PublicSlugClaimDocument | None:
        """
        The claim of an address, or None when nobody took it (or, inside a
        business's storage scope, when another business took it).
        """
        raise NotImplementedError
