"""The cancel dialog's offers and the pause card as the cabinet shows them."""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.subscription_lifecycle import RetentionOfferKind
from app.schemas.dto.billing import Money
from app.schemas.dto.catalog.plan_quotes import QuotedMoney
from app.schemas.dto.subscription_lifecycle import (
    PauseOptionsView,
    RetentionOfferView,
)
from app.schemas.dto.subscription_lifecycle_policy import SubscriptionLifecyclePolicy
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.subscription_lifecycle.booleans import IsPauseAvailable
from app.use_cases.billing.lifecycle.retention_offers import OfferInputs
from app.use_cases.shared.subscription_pricing import quote_money


def quote(money: Money | None, language: LanguageTag) -> QuotedMoney | None:
    return None if money is None else quote_money(money, False, language)


def view_pause(
    inputs: OfferInputs,
    policy: SubscriptionLifecyclePolicy,
    language: LanguageTag,
) -> PauseOptionsView:
    return PauseOptionsView(
        is_enabled=inputs.pause.is_enabled,
        is_available=IsPauseAvailable(inputs.pause.unavailable_reason is None),
        unavailable_reason=inputs.pause.unavailable_reason,
        price_percent=policy.pause_price_percent,
        monthly_price=quote(inputs.pause_price, language),
        starts_at=inputs.pause.starts_at,
        max_months=inputs.pause.max_months,
        paused_months=inputs.pause.paused_months,
        cap_months=policy.max_pause_months,
        window_months=policy.pause_window_months,
    )


def view_offer(
    kind: RetentionOfferKind,
    inputs: OfferInputs,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> RetentionOfferView:
    match kind:
        case RetentionOfferKind.PAUSE:
            return RetentionOfferView(
                kind=kind,
                pause_months=inputs.pause.max_months,
                pause_price=quote(inputs.pause_price, language),
            )
        case RetentionOfferKind.DOWNGRADE:
            return RetentionOfferView(
                kind=kind,
                plan_key=None
                if inputs.cheaper_plan is None
                else inputs.cheaper_plan.key,
                plan_name=(
                    None
                    if inputs.cheaper_plan is None
                    else resolver.resolve(inputs.cheaper_plan.names, language)
                ),
                plan_price=quote(inputs.cheaper_price, language),
            )
        case RetentionOfferKind.CREDIT:
            return RetentionOfferView(
                kind=kind, credit=quote(inputs.save_credit, language)
            )
