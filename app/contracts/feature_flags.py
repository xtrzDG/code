"""The feature flags of staged rollouts and the gate that reads them (REL-08)."""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.contracts.utility_contract import UtilityContract
from app.schemas.constants.feature_flags import FeatureFlagDecision
from app.schemas.domain.feature_flags import FeatureFlagDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.feature_flags.constrained_strings import FeatureFlagName


class FeatureFlagRepoContract(RepoContract, Protocol):
    def get(self, name: FeatureFlagName) -> FeatureFlagDocument | None:
        """The flag as it stands; None when it was never set (off)."""
        raise NotImplementedError

    def get_many(self, names: Sequence[FeatureFlagName]) -> list[FeatureFlagDocument]:
        """The flags of these names that were ever set, by their keys."""
        raise NotImplementedError

    def save(self, flag: FeatureFlagDocument) -> None:
        raise NotImplementedError


class FeatureFlagGateContract(UtilityContract, Protocol):
    """Asked by a release's code at request time: does the flag hold here?"""

    def decide(
        self, name: FeatureFlagName, business_id: BusinessId
    ) -> FeatureFlagDecision:
        """Why the flag holds for the business or not (off when never set)."""
        raise NotImplementedError
