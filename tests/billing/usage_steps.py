"""Steps of the package usage tests: start a trial, read and check usage."""

from app.schemas.constants.billing import PlanKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    BillingOverviewQuery,
    PackageUsageView,
    StartTrialCommand,
    StartTrialRequest,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.billing_settings import GEORGIA, CountryPreset
from tests.billing.billing_testbed import BillingTestbed

SECONDS_IN_MINUTE: int = 60


def start_trial(
    testbed: BillingTestbed,
    country: CountryPreset = GEORGIA,
    plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
) -> tuple[UserDocument, BusinessDocument]:
    owner = (
        testbed.add_user(phone_number="+995599123456")
        if country is GEORGIA
        else testbed.add_user(email="owner@example.it")
    )
    business = testbed.add_business(owner, country, plan_key=plan_key)
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(),
        )
    )
    return owner, business


def read_usage(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
    language: str | None = None,
) -> PackageUsageView:
    overview = testbed.get_overview.run(
        BillingOverviewQuery(
            user_id=owner.id,
            business_id=business.id,
            display_language=None if language is None else LanguageTag(language),
        )
    )
    assert overview.usage is not None
    return overview.usage


def check_usage(testbed: BillingTestbed) -> int:
    return testbed.run_job(testbed.check_package_usage, "check_package_usage")
