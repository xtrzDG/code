"""
Whether a flag holds for a business: off unless switched on; the exclusion
list wins over the inclusion list, which wins over the rollout; a business
falls in a stable bucket, so a widening rollout only ever adds businesses.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.feature_flags import FeatureFlagDecision
from app.schemas.domain.feature_flags import FeatureFlagDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.feature_flags.constrained_integers import (
    FeatureFlagRolloutPercent,
)
from app.schemas.typings.feature_flags.constrained_strings import (
    FeatureFlagChangeReason,
    FeatureFlagName,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.feature_flags.feature_flag_catalog import (
    FEATURE_FLAGS,
    RELEASE_CANARY,
    find_feature_flag,
)
from app.utilities.feature_flags.flag_evaluation import (
    decide,
    is_holding,
    rollout_bucket,
)

BUSINESSES: list[BusinessId] = [BusinessId() for _ in range(2000)]


def flag(
    percent: int,
    is_enabled: bool = True,
    included: list[BusinessId] | None = None,
    excluded: list[BusinessId] | None = None,
) -> FeatureFlagDocument:
    return FeatureFlagDocument(
        name=RELEASE_CANARY,
        is_enabled=is_enabled,
        rollout_percent=FeatureFlagRolloutPercent(percent),
        included_business_ids=included or [],
        excluded_business_ids=excluded or [],
        reason=FeatureFlagChangeReason("Rollout step of the test"),
        changed_by=UserId(),
        changed_at=Microseconds(0),
        created_at=Microseconds(0),
        updated_at=Microseconds(0),
    )


def holding(document: FeatureFlagDocument) -> set[BusinessId]:
    return {b for b in BUSINESSES if is_holding(decide(document, b))}


def test_a_flag_never_set_or_switched_off_holds_for_nobody() -> None:
    business = BUSINESSES[0]

    assert decide(None, business) is FeatureFlagDecision.OFF
    assert decide(flag(100, is_enabled=False), business) is FeatureFlagDecision.OFF
    assert holding(flag(100, is_enabled=False, included=[business])) == set()


def test_the_lists_win_over_the_rollout_and_exclusion_wins_over_all() -> None:
    first, second = BUSINESSES[0], BUSINESSES[1]

    assert decide(flag(0, included=[first]), first) is FeatureFlagDecision.INCLUDED
    assert decide(flag(0, included=[first]), second) in {
        FeatureFlagDecision.OUTSIDE_ROLLOUT
    }
    assert decide(flag(100, excluded=[first]), first) is FeatureFlagDecision.EXCLUDED
    assert (
        decide(flag(100, included=[first], excluded=[first]), first)
        is FeatureFlagDecision.EXCLUDED
    )


def test_the_rollout_reaches_about_its_share_and_only_grows() -> None:
    previous: set[BusinessId] = set()
    for percent in (0, 1, 10, 50, 100):
        reached = holding(flag(percent))
        share = len(reached) / len(BUSINESSES)

        assert previous <= reached
        assert abs(share - percent / 100) < 0.04, (percent, share)
        previous = reached

    assert previous == set(BUSINESSES)


def test_a_bucket_is_stable_and_differs_between_flags() -> None:
    business = BUSINESSES[0]
    other = FeatureFlagName("other_flag")

    assert rollout_bucket(RELEASE_CANARY, business) == rollout_bucket(
        RELEASE_CANARY, business
    )
    assert 0 <= int(rollout_bucket(RELEASE_CANARY, business)) <= 99
    differing = sum(
        rollout_bucket(RELEASE_CANARY, b) != rollout_bucket(other, b)
        for b in BUSINESSES[:200]
    )
    assert differing > 150


def test_the_registry_names_its_flags_and_nothing_else() -> None:
    assert [definition.name for definition in FEATURE_FLAGS] == [RELEASE_CANARY]
    assert find_feature_flag("release_canary") is FEATURE_FLAGS[0]
    assert find_feature_flag("not_a_flag") is None
