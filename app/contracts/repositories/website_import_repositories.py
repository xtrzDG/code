"""
Persistence contract of the website import: the current import of each
business (one per business; a new import replaces a finished one).

Implementations return independent copies: mutating a returned document
does not change stored state until it is saved. The document is looked up
through its business id, so one tenant never sees another's import.
"""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.website_import.prefixed_id import WebsiteImportId


class WebsiteImportRepoContract(RepoContract, Protocol):
    def get_by_business(self, business_id: BusinessId) -> WebsiteImportDocument | None:
        """The business's current website import, if it ever had one."""
        raise NotImplementedError

    def start(
        self,
        website_import: WebsiteImportDocument,
        stale_before: Microseconds,
    ) -> WebsiteImportDocument | None:
        """
        Make `website_import` the business's current import in one atomic
        step, unless its current import is still queued or reading and was
        updated at or after `stale_before`. Returns that import when it
        blocks the new one, else None (the new one is stored).
        """
        raise NotImplementedError

    def change(
        self,
        business_id: BusinessId,
        import_id: WebsiteImportId,
        apply: Callable[[WebsiteImportDocument], bool],
    ) -> WebsiteImportDocument | None:
        """
        Change the business's current import in one atomic step when it is
        still `import_id` and `apply` returns True; returns what was stored,
        or None when it was replaced, is missing, or `apply` declined.
        """
        raise NotImplementedError
