"""
"Apply changes" whose checks were queued before a platform brake (the
global pause, the daily budget stop): the worker skips the run as it
starts, and the apply must not stay CHECKING forever; it waits for the
owner like checks that stopped, and nothing goes live.
"""

import pytest

from app.schemas.constants.setup import ApplyAttentionCode
from app.schemas.constants.spend import PlatformBrake
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.testbed import AssemblyTestbed
from tests.setup.apply_testbed import apply, assert_needs_attention, progress, settle


@pytest.mark.parametrize("brake", [PlatformBrake.PAUSED, PlatformBrake.BUDGET_STOP])
def test_checks_skipped_by_a_brake_stop_the_apply(brake: PlatformBrake) -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    apply(testbed, business)
    testbed.platform_brakes.brake = brake

    testbed.run_worker()

    assert_needs_attention(
        progress(testbed, business), ApplyAttentionCode.CHECKS_STOPPED
    )
    assert testbed.business(business.id).published_assistant_version_id is None


def test_a_repeated_checks_job_changes_nothing_after_the_apply_went_live() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_italian_restaurant(testbed))
    apply(testbed, business)
    testbed.run_worker()
    live = progress(testbed, business)

    testbed.run_worker()

    assert progress(testbed, business) == live
