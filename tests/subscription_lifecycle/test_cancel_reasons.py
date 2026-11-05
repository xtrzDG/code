"""Cancelling says why; the routes take the reason, the pause and the offers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.billing_lifecycle_routes import build_billing_lifecycle_router
from app.gateways.http.billing_routes import build_billing_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
    SubscriptionEventKind,
)
from app.schemas.dto.billing_cabinet import CancelSubscriptionCommand
from app.schemas.dto.subscription_lifecycle import CancelSubscriptionRequest
from app.schemas.typings.subscription_lifecycle.constrained_strings import (
    CancellationDetails,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.billing.billing_fakes import TokenAuthenticationOperator, build_operator
from tests.billing.billing_testbed import bearer
from tests.subscription_lifecycle.lifecycle_world import LifecycleWorld
from tests.subscription_lifecycle.pause_steps import pause


def client_for(world: LifecycleWorld) -> TestClient:
    current_user = build_current_user_dependency(
        TokenAuthenticationOperator(world.user_repo), SessionAssuranceContext()
    )
    application = FastAPI()
    install_error_handlers(application)
    application.include_router(
        build_billing_router(
            get_billing_overview_operator=build_operator(world.get_overview),
            start_trial_operator=build_operator(world.start_trial),
            change_plan_operator=build_operator(world.change_plan),
            cancel_subscription_operator=build_operator(world.cancel_subscription),
            start_checkout_operator=build_operator(world.start_checkout),
            subscribe_operator=PipelineOperator(OrchestratorPipeline(world.subscribe)),
            payment_webhook_operator=build_operator(world.process_webhook),
            current_user=current_user,
        )
    )
    application.include_router(
        build_billing_lifecycle_router(
            get_subscription_lifecycle_operator=build_operator(world.get_lifecycle),
            pause_subscription_operator=build_operator(world.pause),
            resume_subscription_operator=build_operator(world.resume),
            accept_retention_offer_operator=build_operator(world.accept_offer),
            current_user=current_user,
        )
    )
    return TestClient(application)


def test_a_cancellation_records_the_reason_the_words_and_the_offer_turned_down() -> (
    None
):
    world = LifecycleWorld()
    owner, business = world.paying_business()

    world.cancel_subscription.run(
        CancelSubscriptionCommand(
            user_id=owner.id,
            business_id=business.id,
            request=CancelSubscriptionRequest(
                reason=CancellationReason.SEASONAL_BREAK,
                details=CancellationDetails("We close for the winter."),
                declined_offer=RetentionOfferKind.PAUSE,
            ),
        )
    )

    [cancelled] = world.steps(business)
    assert cancelled.kind is SubscriptionEventKind.CANCELLED
    assert cancelled.cancellation_reason is CancellationReason.SEASONAL_BREAK
    assert str(cancelled.details) == "We close for the winter."
    assert cancelled.offer_kind is RetentionOfferKind.PAUSE
    assert cancelled.actor_id == owner.id
    # Cancelling twice records nothing more.
    world.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
    )
    assert len(world.steps(business)) == 1


def test_cancelling_calls_off_a_scheduled_pause() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    pause(world, owner, business, months=2)

    world.cancel_subscription.run(
        CancelSubscriptionCommand(user_id=owner.id, business_id=business.id)
    )

    cancelled = world.current(business)
    assert cancelled.status is SubscriptionStatus.CANCELLED
    assert cancelled.pause_starts_at is None and cancelled.pause_until is None
    kinds = [step.kind for step in world.steps(business)]
    assert kinds == [
        SubscriptionEventKind.PAUSE_SCHEDULED,
        SubscriptionEventKind.RESUMED,
        SubscriptionEventKind.CANCELLED,
    ]
    assert world.steps(business)[-1].cancellation_reason is None


def test_the_cancel_route_takes_a_reason_or_none() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    client = client_for(world)
    path = f"/v1/businesses/{business.id}/billing/cancel"

    too_long = client.post(
        path, headers=bearer(owner), json={"reason": "other", "details": "x" * 1001}
    )
    assert too_long.status_code == 422
    answered = client.post(
        path,
        headers=bearer(owner),
        json={"reason": "too_expensive", "declined_offer": "downgrade"},
    )
    assert answered.status_code == 200
    assert answered.json()["subscription"]["status"] == "cancelled"
    assert world.steps(business)[-1].cancellation_reason is (
        CancellationReason.TOO_EXPENSIVE
    )


def test_an_older_cabinet_still_cancels_without_a_body() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()

    response = client_for(world).post(
        f"/v1/businesses/{business.id}/billing/cancel", headers=bearer(owner)
    )

    assert response.status_code == 200
    assert world.steps(business)[-1].cancellation_reason is None


def test_the_lifecycle_routes_offer_pause_and_resume() -> None:
    world = LifecycleWorld()
    owner, business = world.paying_business()
    client = client_for(world)
    base = f"/v1/businesses/{business.id}/billing"

    lifecycle = client.get(f"{base}/lifecycle?language=ru", headers=bearer(owner))
    assert lifecycle.status_code == 200
    body = lifecycle.json()
    assert body["pause"]["is_available"] is True
    assert body["pause"]["max_months"] == 4
    assert body["pause"]["monthly_price"]["text"] == "77,55\xa0GEL"
    seasonal = next(o for o in body["offers"] if o["reason"] == "seasonal_break")
    assert seasonal["offer"]["kind"] == "pause"

    too_many = client.post(f"{base}/pause", headers=bearer(owner), json={"months": 5})
    assert too_many.status_code == 422
    paused = client.post(f"{base}/pause", headers=bearer(owner), json={"months": 2})
    assert paused.status_code == 200
    # The card showed the same end for two months before the owner chose.
    assert paused.json()["subscription"]["pause_until"] == body["pause"]["ends_at"][1]
    assert len(body["pause"]["ends_at"]) == 4
    again = client.post(f"{base}/pause", headers=bearer(owner), json={"months": 1})
    assert again.status_code == 409

    resumed = client.post(f"{base}/resume", headers=bearer(owner))
    assert resumed.status_code == 200
    assert resumed.json()["subscription"]["pause_until"] is None

    accepted = client.post(
        f"{base}/offers/accept",
        headers=bearer(owner),
        json={"reason": "too_expensive", "kind": "downgrade"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["subscription"]["plan_key"] == "chat"
    refused = client.post(
        f"{base}/offers/accept",
        headers=bearer(owner),
        json={"reason": "closing_business", "kind": "credit"},
    )
    assert refused.status_code == 409


def test_the_pause_route_is_refused_while_pausing_is_off() -> None:
    world = LifecycleWorld(is_pause_enabled=False)
    owner, business = world.paying_business()

    response = client_for(world).post(
        f"/v1/businesses/{business.id}/billing/pause",
        headers=bearer(owner),
        json={"months": 1},
    )

    assert response.status_code == 409
    assert world.current(business).pause_until is None
