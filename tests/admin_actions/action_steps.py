"""The account actions of the tests, as an admin would ask for them."""

from collections.abc import Callable

from app.schemas.constants.billing import (
    BillingPeriod,
    ManualPaymentMethod,
    PlanKey,
)
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_actions import (
    AdminActionReceipt,
    AdminReasonBody,
    ExtendTrialBody,
    ExtendTrialCommand,
    GiveDiscountBody,
    GiveDiscountCommand,
    GrantCreditBody,
    GrantCreditCommand,
    MarkInvoicePaidBody,
    MarkInvoicePaidCommand,
    OverridePlanBody,
    OverridePlanCommand,
    WaiveSetupFeeCommand,
)
from app.schemas.typings.billing.constrained_integers import (
    BillingCreditAmountMinor,
    ClientDiscountPercent,
    TrialExtensionDays,
)
from app.schemas.typings.billing.constrained_strings import (
    DiscountEndDate,
    ManualPaymentReference,
)
from app.schemas.typings.billing.prefixed_id import InvoiceId
from tests.admin_actions.action_world import ADMIN_IP, REASON, ActionWorld

type Act = Callable[[ActionWorld, UserDocument], AdminActionReceipt]


def extend(world: ActionWorld, admin: UserDocument) -> AdminActionReceipt:
    return world.extend_trial.run(
        ExtendTrialCommand(
            user_id=admin.id,
            business_id=world.business.id,
            body=ExtendTrialBody(days=TrialExtensionDays(7), reason=REASON),
            client_ip_address=ADMIN_IP,
        )
    )


def discount(world: ActionWorld, admin: UserDocument) -> AdminActionReceipt:
    return world.give_discount.run(
        GiveDiscountCommand(
            user_id=admin.id,
            business_id=world.business.id,
            body=GiveDiscountBody(
                percent=ClientDiscountPercent(30),
                last_day=DiscountEndDate("2027-12-31"),
                reason=REASON,
            ),
        )
    )


def credit(world: ActionWorld, admin: UserDocument) -> AdminActionReceipt:
    return world.grant_credit.run(
        GrantCreditCommand(
            user_id=admin.id,
            business_id=world.business.id,
            body=GrantCreditBody(
                amount_minor=BillingCreditAmountMinor(10_000), reason=REASON
            ),
        )
    )


def waive(world: ActionWorld, admin: UserDocument) -> AdminActionReceipt:
    return world.waive_setup_fee.run(
        WaiveSetupFeeCommand(
            user_id=admin.id,
            business_id=world.business.id,
            body=AdminReasonBody(reason=REASON),
        )
    )


def mark_paid(
    world: ActionWorld, admin: UserDocument, invoice_id: InvoiceId | None = None
) -> AdminActionReceipt:
    return world.mark_invoice_paid.run(
        MarkInvoicePaidCommand(
            user_id=admin.id,
            business_id=world.business.id,
            invoice_id=invoice_id or InvoiceId(),
            body=MarkInvoicePaidBody(
                method=ManualPaymentMethod.BANK_TRANSFER,
                reference=ManualPaymentReference("TBC #1"),
                reason=REASON,
            ),
        )
    )


def override(world: ActionWorld, admin: UserDocument) -> AdminActionReceipt:
    return world.override_plan.run(
        OverridePlanCommand(
            user_id=admin.id,
            business_id=world.business.id,
            body=OverridePlanBody(
                plan_key=PlanKey.CHAT,
                billing_period=BillingPeriod.MONTHLY,
                reason=REASON,
            ),
        )
    )
