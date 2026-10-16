"""Why applied changes did not go live, in plain words and with where to fix it."""

from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.setup import (
    ApplyAttentionCode,
    ApplyChangesStage,
    SetupActionTarget,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from tests.assembly.builders import build_business, make_launch_ready
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.publish_helpers import only_subscription
from tests.assembly.testbed import AssemblyTestbed
from tests.setup.apply_testbed import (
    apply,
    assert_needs_attention,
    progress,
    settle,
    stored_apply,
)


def test_missing_launch_conditions_stop_the_apply_before_any_check() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed, is_launch_ready=False)

    view = apply(testbed, business)

    assert_needs_attention(
        view,
        ApplyAttentionCode.AGREEMENT_NOT_ACCEPTED,
        ApplyAttentionCode.STAFF_CONTACT_MISSING,
    )
    # The version was built, but no check was started for it.
    assert view.assistant_version_id is not None
    assert testbed.pending_jobs() == []
    version = testbed.version(business.id, view.assistant_version_id)
    assert version.status is AssistantVersionStatus.DRAFT
    targets = [reason.action.target for reason in view.attention]
    assert targets == [SetupActionTarget.AGREEMENT, SetupActionTarget.STAFF_CONTACTS]
    assert view.attention[1].details == ["no_handoff_contact"]


def test_reasons_are_worded_in_the_requested_language() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed, is_launch_ready=False)
    apply(testbed, business)

    english = progress(testbed, business, "en")
    russian = progress(testbed, business, "ru")
    georgian = progress(testbed, business, "ka")

    assert english.attention[0].message == (
        "Accept the data processing agreement to go live."
    )
    assert russian.attention[0].message == (
        "Чтобы запустить помощника, примите соглашение об обработке данных."
    )
    assert georgian.attention[0].message.startswith("ასისტენტის გასაშვებად")
    assert english.attention[0].action.label != russian.attention[0].action.label


def test_an_ended_trial_asks_for_payment() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    subscription = only_subscription(testbed, business)
    subscription.trial_ends_at = testbed.wall_clock.now_unix()
    testbed.subscription_repo.save(subscription)

    view = apply(testbed, business)

    assert_needs_attention(view, ApplyAttentionCode.PAYMENT_NEEDED)
    assert view.attention[0].action.target is SetupActionTarget.BILLING
    assert view.attention[0].details == [SubscriptionStatus.TRIALING.value]


def test_failed_checks_leave_the_version_unpublished_with_the_failed_kinds() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    for language in ("it", "en"):
        testbed.judge_scores[f"booking__{language}"] = {
            "facts_and_prices": 1,
            "booking_data": 1,
            "ai_disclosure": 1,
            "handoff": 1,
            "language": 1,
        }

    started = apply(testbed, business)
    assert started.stage is ApplyChangesStage.CHECKING
    testbed.run_worker()
    view = progress(testbed, business)

    assert_needs_attention(view, ApplyAttentionCode.CHECKS_FAILED)
    assert view.attention[0].details == ["booking"]
    assert view.attention[0].action.target is SetupActionTarget.CHECKS
    assert testbed.business(business.id).published_assistant_version_id is None


def test_voice_that_cannot_be_set_up_keeps_the_checked_version_waiting() -> None:
    testbed = AssemblyTestbed()
    business = settle(testbed, seed_georgian_restaurant(testbed))
    testbed.voice_provisioner.error = ExternalServiceError("ElevenLabs is down")

    apply(testbed, business)
    testbed.run_worker()
    view = progress(testbed, business)

    assert_needs_attention(view, ApplyAttentionCode.VOICE_NOT_READY)
    assert view.attention[0].action.target is SetupActionTarget.APPLY_CHANGES
    assert testbed.business(business.id).published_assistant_version_id is None
    assert view.assistant_version_id is not None
    checked = testbed.version(business.id, view.assistant_version_id)
    assert checked.status is AssistantVersionStatus.READY
    # Applying again publishes the checked version without new checks.
    testbed.voice_provisioner.error = None
    again = apply(testbed, business)
    assert again.stage is ApplyChangesStage.LIVE
    assert again.assistant_version_id == view.assistant_version_id
    assert testbed.pending_jobs() == []
    assert len(testbed.version_repo.list_by_business(business.id)) == 1


def test_a_condition_lost_during_the_checks_is_reported_at_publishing() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    apply(testbed, business)
    stored = testbed.business(business.id)
    stored.manager_contacts = []
    testbed.business_repo.save(stored)

    testbed.run_worker()
    view = progress(testbed, business)

    assert_needs_attention(view, ApplyAttentionCode.STAFF_CONTACT_MISSING)
    assert testbed.business(business.id).published_assistant_version_id is None


def test_a_profile_with_blocking_gaps_is_not_checked() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    profile = testbed.profile_repo.get_by_business(business.id)
    assert profile is not None
    profile.hours = []
    testbed.profile_repo.save(profile)

    view = apply(testbed, business)

    assert_needs_attention(view, ApplyAttentionCode.PROFILE_INCOMPLETE)
    assert "no_opening_hours" in view.attention[0].details
    assert view.attention[0].action.target is SetupActionTarget.PROFILE
    assert testbed.pending_jobs() == []


def test_a_business_without_a_profile_cannot_be_built() -> None:
    testbed = AssemblyTestbed()
    business = build_business(
        testbed,
        name="Nuovo",
        niche_key=NicheKey.RESTAURANT,
        country_code="IT",
        city=None,
        timezone_name="Europe/Rome",
        currency_code="EUR",
        languages=["it"],
    )

    view = apply(testbed, business)

    assert_needs_attention(view, ApplyAttentionCode.PROFILE_INCOMPLETE)
    assert view.assistant_version_id is None
    assert testbed.version_repo.list_by_business(business.id) == []


def test_after_fixing_the_owner_applies_again_and_goes_live() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed, is_launch_ready=False)
    first = apply(testbed, business)
    assert first.stage is ApplyChangesStage.NEEDS_ATTENTION

    make_launch_ready(testbed, testbed.business(business.id))
    second = apply(testbed, business)
    testbed.run_worker()
    view = progress(testbed, business)

    assert second.stage is ApplyChangesStage.CHECKING
    assert view.stage is ApplyChangesStage.LIVE
    assert view.attention == []
    assert stored_apply(testbed, business).attention == []
    assert testbed.business(business.id).published_assistant_version_id == (
        view.assistant_version_id
    )
