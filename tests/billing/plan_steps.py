"""Steps of the trial and plan tests: start a trial and change the plan."""

from app.schemas.constants.billing import BillingPeriod, PlanKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    BillingOverview,
    ChangePlanCommand,
    ChangePlanRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.billing_testbed import BillingTestbed


def start_trial(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
    plan_key: PlanKey | None = None,
    billing_period: BillingPeriod = BillingPeriod.MONTHLY,
    language: str | None = None,
) -> BillingOverview:
    return testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(plan_key=plan_key, billing_period=billing_period),
            display_language=None if language is None else LanguageTag(language),
        )
    )


def change_plan(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
    plan_key: PlanKey,
    billing_period: BillingPeriod,
) -> BillingOverview:
    return testbed.change_plan.run(
        ChangePlanCommand(
            user_id=owner.id,
            business_id=business.id,
            request=ChangePlanRequest(plan_key=plan_key, billing_period=billing_period),
        )
    )
