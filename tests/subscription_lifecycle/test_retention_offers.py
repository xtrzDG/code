"""The cancel dialog's offer for each reason, as the business stands now."""

import pytest

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    PauseUnavailableReason,
    RetentionOfferKind,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.dto.subscription_lifecycle import (
    AcceptRetentionOfferCommand,
    AcceptRetentionOfferRequest,
    RetentionOfferView,
    SubscriptionLifecycleQuery,
)
from app.schemas.exceptions.application_errors import AccessDeniedError
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld

PAUSE = RetentionOfferKind.PAUSE
DOWNGRADE = RetentionOfferKind.DOWNGRADE
CREDIT = RetentionOfferKind.CREDIT


def offers(
    world: LifecycleWorld, business: BusinessDocument
) -> dict[CancellationReason, RetentionOfferView | None]:
    return {
        choice.reason: choice.offer for choice in world.lifecycle_of(business).offers
    }


def kinds(
    world: LifecycleWorld, business: BusinessDocument
) -> dict[CancellationReason, RetentionOfferKind | None]:
    return {
        reason: None if offer is None else offer.kind
        for reason, offer in offers(world, business).items()
    }


def test_every_reason_gets_its_offer_on_a_paid_monthly_plan() -> None:
    world = LifecycleWorld()
    _, business = world.paying_business()

    assert kinds(world, business) == {
        CancellationReason.TOO_EXPENSIVE: DOWNGRADE,
        CancellationReason.SEASONAL_BREAK: PAUSE,
        CancellationReason.NOT_ENOUGH_USE: PAUSE,
        CancellationReason.MISSING_FEATURE: CREDIT,
        CancellationReason.ANSWER_QUALITY: CREDIT,
        CancellationReason.SWITCHED_PROVIDER: CREDIT,
        CancellationReason.CLOSING_BUSINESS: None,
        CancellationReason.OTHER: PAUSE,
    }
    # The dialog lists the reasons in this order.
    assert [choice.reason for choice in world.lifecycle_of(business).offers] == list(
        CancellationReason
    )


def test_offers_name_their_terms_in_the_subscription_currency() -> None:
    world = LifecycleWorld()
    _, business = world.paying_business()
    by_reason = offers(world, business)

    downgrade = by_reason[CancellationReason.TOO_EXPENSIVE]
    assert downgrade is not None and downgrade.plan_key is PlanKey.CHAT
    assert downgrade.plan_price is not None
    assert int(downgrade.plan_price.money.amount_minor) == 29300
    pause = by_reason[CancellationReason.SEASONAL_BREAK]
    assert pause is not None and pause.pause_months == 4
    # 15% of 517.00 GEL a month.
    assert pause.pause_price is not None
    assert int(pause.pause_price.money.amount_minor) == 7755
    credit = by_reason[CancellationReason.ANSWER_QUALITY]
    assert credit is not None and credit.credit is not None
    # Half a month of the plan, once.
    assert int(credit.credit.money.amount_minor) == 25850
    assert str(credit.credit.money.currency_code) == "GEL"


def test_without_the_pause_switched_on_the_seasonal_reasons_get_no_pause() -> None:
    world = LifecycleWorld(is_pause_enabled=False)
    _, business = world.paying_business()

    by_reason = kinds(world, business)
    assert by_reason[CancellationReason.SEASONAL_BREAK] is None
    assert by_reason[CancellationReason.NOT_ENOUGH_USE] is DOWNGRADE
    assert by_reason[CancellationReason.TOO_EXPENSIVE] is DOWNGRADE
    assert by_reason[CancellationReason.OTHER] is None
    pause = world.lifecycle_of(business).pause
    assert pause.is_enabled is False and pause.is_available is False
    assert pause.unavailable_reason is PauseUnavailableReason.FEATURE_OFF


def test_the_cheapest_plan_is_offered_a_pause_or_credit_instead_of_a_downgrade() -> (
    None
):
    world = LifecycleWorld()
    _, business = world.paying_business(plan_key=PlanKey.CHAT)
    assert kinds(world, business)[CancellationReason.TOO_EXPENSIVE] is PAUSE

    world_without_pause = LifecycleWorld(is_pause_enabled=False)
    _, chat_business = world_without_pause.paying_business(plan_key=PlanKey.CHAT)
    assert (
        kinds(world_without_pause, chat_business)[CancellationReason.TOO_EXPENSIVE]
        is CREDIT
    )


def test_a_trial_cannot_pause_but_can_move_down_or_take_the_credit() -> None:
    world = LifecycleWorld()
    _, business = world.trialing_business()

    by_reason = kinds(world, business)
    assert by_reason[CancellationReason.SEASONAL_BREAK] is None
    assert by_reason[CancellationReason.TOO_EXPENSIVE] is DOWNGRADE
    assert by_reason[CancellationReason.ANSWER_QUALITY] is CREDIT
    pause = world.lifecycle_of(business).pause
    assert pause.unavailable_reason is PauseUnavailableReason.NOT_ACTIVE


def test_the_credit_is_offered_once_per_business() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    world.accept_offer.run(
        AcceptRetentionOfferCommand(
            user_id=owner.id,
            business_id=business.id,
            request=AcceptRetentionOfferRequest(
                reason=CancellationReason.MISSING_FEATURE, kind=CREDIT
            ),
        )
    )

    by_reason = kinds(world, business)
    assert by_reason[CancellationReason.MISSING_FEATURE] is None
    assert by_reason[CancellationReason.ANSWER_QUALITY] is None


def test_only_owners_read_the_offers() -> None:
    world = LifecycleWorld()
    _, business = world.paying_business()
    staff = world.add_user(email="staff@example.com")
    stored = world.business(business.id)
    stored.members.append(
        BusinessMember(user_id=staff.id, role=BusinessMemberRole.STAFF)
    )
    world.business_repo.save(stored)

    with pytest.raises(AccessDeniedError):
        world.get_lifecycle.run(
            SubscriptionLifecycleQuery(user_id=staff.id, business_id=business.id)
        )
