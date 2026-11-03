from app.contracts.feature_flags import FeatureFlagGateContract, FeatureFlagRepoContract
from app.schemas.constants.feature_flags import FeatureFlagDecision
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.feature_flags.constrained_strings import FeatureFlagName
from app.utilities.feature_flags.flag_evaluation import decide


class FeatureFlagGate(FeatureFlagGateContract):
    """
    The flag gate (REL-08): reads the flag by its key on every question, so
    an admin's change holds at the next request of every process, with no
    cache to wait out or to restart.
    """

    def __init__(self, flag_repo: FeatureFlagRepoContract) -> None:
        self._flag_repo: FeatureFlagRepoContract = flag_repo

    def decide(
        self, name: FeatureFlagName, business_id: BusinessId
    ) -> FeatureFlagDecision:
        return decide(self._flag_repo.get(name), business_id)
