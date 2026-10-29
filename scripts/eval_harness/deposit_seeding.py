"""
Deposits for a dataset's business (`business.deposits`), set the way an
owner sets them in the cabinet: one payment page template, deposits
turned on, and on each of the business's resources a deposit per guest
from a number of guests. A booking that big then asks its deposit in the
scenario (create_booking's result says so, send_payment_link issues it
and the platform writes the payment line under the reply).
"""

from decimal import Decimal

from pydantic import Field

from app.containers.app import AppContainer
from app.schemas.constants.deposits import DepositRule, DepositTarget, PaymentLinkKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.deposits.deposit_settings import (
    AddPaymentLinkCommand,
    DepositPolicyInput,
    DepositPolicyRequest,
    DepositSettingsRequest,
    PaymentLinkInput,
    SetDepositPolicyCommand,
    UpdateDepositSettingsCommand,
)
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.deposits.constrained_integers import (
    DepositAmountMinor,
    DepositHoldMinutes,
)
from app.schemas.typings.deposits.constrained_strings import (
    PaymentLinkAddressInput,
    PaymentLinkLabel,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.money.money_math import build_money_from_major_units
from scripts.eval_harness.strict_model import StrictModel

PAGE_LABEL: str = "Bank"


class DepositSpec(StrictModel):
    """
    `page`: the owner's https payment page with {amount} and {reference};
    `per_guest`: the deposit of one guest (major units of the business
    currency), asked from `min_party_size` guests on; `hold_minutes`: how
    long a held place waits for the payment.
    """

    page: str
    per_guest: str
    min_party_size: int = Field(ge=1)
    hold_minutes: int = Field(default=60, ge=15, le=1440)


def seed_deposits(
    container: AppContainer,
    owner_id: UserId,
    business: BusinessDocument,
    deposits: DepositSpec,
) -> None:
    """Called inside the business's storage scope, as its owner."""

    use_cases = container.use_cases.deposits
    use_cases.add_payment_link_use_case().run(
        AddPaymentLinkCommand(
            user_id=owner_id,
            business_id=business.id,
            link=PaymentLinkInput(
                label=PaymentLinkLabel(PAGE_LABEL),
                kind=PaymentLinkKind.TEMPLATE,
                address=PaymentLinkAddressInput(deposits.page),
            ),
        )
    )
    use_cases.update_deposit_settings_use_case().run(
        UpdateDepositSettingsCommand(
            user_id=owner_id,
            business_id=business.id,
            request=DepositSettingsRequest(
                is_enabled=True, hold_minutes=DepositHoldMinutes(deposits.hold_minutes)
            ),
        )
    )
    per_guest = build_money_from_major_units(
        Decimal(deposits.per_guest), business.currency_code
    )
    set_policy = use_cases.set_deposit_policy_use_case()
    for resource in container.repositories.resource_repo().list_by_business(
        business.id
    ):
        set_policy.run(
            SetDepositPolicyCommand(
                user_id=owner_id,
                business_id=business.id,
                request=DepositPolicyRequest(
                    target=DepositTarget.RESOURCE,
                    resource_id=resource.id,
                    policy=DepositPolicyInput(
                        rule=DepositRule.PER_GUEST,
                        amount_minor=DepositAmountMinor(int(per_guest.amount_minor)),
                        min_party_size=PartySize(deposits.min_party_size),
                    ),
                ),
            )
        )
