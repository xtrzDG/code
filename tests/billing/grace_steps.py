"""Steps of the trial-end and grace period tests: start, pay and run the jobs."""

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    StartCheckoutCommand,
    StartCheckoutRequest,
    StartTrialCommand,
    StartTrialRequest,
)
from tests.billing.billing_settings import GEORGIA, CountryPreset
from tests.billing.billing_testbed import BillingTestbed


def start_trial(
    testbed: BillingTestbed,
    country: CountryPreset = GEORGIA,
) -> tuple[UserDocument, BusinessDocument]:
    owner = (
        testbed.add_user(phone_number="+995599123456")
        if country is GEORGIA
        else testbed.add_user(email="owner@example.it", display_name="Giulia")
    )
    business = testbed.add_business(owner, country, name="Trattoria")
    testbed.start_trial.run(
        StartTrialCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartTrialRequest(),
        )
    )
    testbed.set_up_for_you(business.id)
    return owner, business


def pay_open_invoices(
    testbed: BillingTestbed,
    owner: UserDocument,
    business: BusinessDocument,
    payment_id: int = 1,
) -> None:
    session = testbed.start_checkout.run(
        StartCheckoutCommand(
            user_id=owner.id,
            business_id=business.id,
            request=StartCheckoutRequest(),
        )
    )
    order = testbed.payment_order_repo.get(session.payment_order_id)
    assert order is not None
    testbed.deliver_flitt_callback(
        testbed.callback_parameters(order, "approved", payment_id=payment_id)
    )


def end_trial(testbed: BillingTestbed) -> int:
    return testbed.run_job(testbed.end_trials, "end_trials")


def enforce(testbed: BillingTestbed) -> int:
    return testbed.run_job(testbed.enforce_grace_periods, "enforce_grace_periods")
